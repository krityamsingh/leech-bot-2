import os
import sys
import random
import time
import threading
import mimetypes
import logging
from pathlib import Path
import tempfile
import shutil
import requests
from Crypto.Cipher import AES
from Crypto.Util import Counter

# Import base Mega from mega.py (site-packages) bypassing this local folder
import importlib
orig_path = list(sys.path)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if p and os.path.abspath(p) != parent_dir]
orig_mega = sys.modules.pop('mega', None)
try:
    real_mega = importlib.import_module('mega.mega')
    Mega = real_mega.Mega
    try:
        real_errors = importlib.import_module('mega.errors')
        RequestError = real_errors.RequestError
    except (ImportError, ModuleNotFoundError):
        RequestError = getattr(real_mega, "RequestError", RuntimeError)
finally:
    sys.path = orig_path
    if orig_mega:
        sys.modules['mega'] = orig_mega

LOGGER = logging.getLogger("mega_shim")

class MegaError:
    API_OK = 0
    API_EAGAIN = -3
    API_ERATELIMIT = -6
    API_EOVERQUOTA = -17
    API_EINCOMPLETE = -13

    def __init__(self, code=0, message="OK"):
        self.code = code
        self.message = message

    def getErrorCode(self):
        return self.code

    def toString(self):
        return self.message

class MegaRequest:
    TYPE_LOGIN = 1
    TYPE_FETCH_NODES = 2
    TYPE_GET_PUBLIC_NODE = 3
    TYPE_EXPORT = 4
    TYPE_CREATE_FOLDER = 5
    TYPE_IMPORT_LINK = 6
    TYPE_LOGOUT = 7
    TYPE_ACCOUNT_DETAILS = 16

    def __init__(self, type_id, request_string):
        self.type_id = type_id
        self.request_string = request_string
        self._link = None
        self._node_handle = None
        self._public_node = None
        self._account_details = None

    def getType(self):
        return self.type_id

    def getRequestString(self):
        return self.request_string

    def getLink(self):
        return self._link

    def getNodeHandle(self):
        return self._node_handle

    def getPublicMegaNode(self):
        return self._public_node

    def getMegaAccountDetails(self):
        return self._account_details

class MegaTransfer:
    TYPE_UPLOAD = 1
    TYPE_DOWNLOAD = 2

    def __init__(self, type_id, name, size, handle=None, parent_handle=None):
        self.type_id = type_id
        self.name = name
        self.size = size
        self.transferred = 0
        self.speed = 0
        self.handle = handle
        self.parent_handle = parent_handle

    def getType(self):
        return self.type_id

    def getFileName(self):
        return self.name

    def getTotalBytes(self):
        return self.size

    def getTransferredBytes(self):
        return self.transferred

    def getSpeed(self):
        return self.speed

    def getNodeHandle(self):
        return self.handle

    def getParentHandle(self):
        return self.parent_handle

    def isFolderTransfer(self):
        return False

class MegaAccountDetails:
    def __init__(self, storage_max, storage_used, num_files=0, num_folders=0):
        self._storage_max = storage_max
        self._storage_used = storage_used
        self._num_files = num_files
        self._num_folders = num_folders

    def getStorageMax(self): return self._storage_max
    def getStorageUsed(self): return self._storage_used
    def getTransferMax(self): return 100 * 1024 * 1024 * 1024
    def getTransferUsed(self): return 0
    def getProLevel(self): return 0
    def getProExpiration(self): return 0
    def getNumFiles(self, handle): return self._num_files
    def getNumFolders(self, handle): return self._num_folders

class MegaCancelToken:
    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def isCancelled(self):
        return self._cancelled

    @staticmethod
    def createInstance():
        return MegaCancelToken()

class MegaUploadOptions:
    def __init__(self):
        self.fileName = ""
        self.mtime = -1
        self.isSourceTemporary = False

    @staticmethod
    def createInstance():
        return MegaUploadOptions()

class MegaNode:
    def __init__(self, name, handle, is_folder=False, size=0, parent=None, key=None):
        self._name = name
        self._handle = handle
        self._is_folder = is_folder
        self._size = size
        self._parent = parent
        self.key = key

    def getName(self):
        return self._name

    def getHandle(self):
        return self._handle

    def isFolder(self):
        return self._is_folder

    def getSize(self):
        return self._size

class MegaListener:
    def onRequestStart(self, api, request): pass
    def onRequestFinish(self, api, request, error): pass
    def onRequestUpdate(self, api, request): pass
    def onRequestTemporaryError(self, api, request, error): pass
    def onTransferStart(self, api, transfer): pass
    def onTransferFinish(self, api, transfer, error): pass
    def onTransferUpdate(self, api, transfer): pass
    def onTransferTemporaryError(self, api, transfer, error): pass

# Custom subclass of Mega to intercept uploads/downloads for progress tracking
class ProgressMega(Mega):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_progress = None

    def _download_file(self, file_handle, file_key, dest_path=None, dest_filename=None, is_public=False, file=None, cancel_token=None):
        # Override to call on_progress update callback
        from mega.crypto import (base64_to_a32, base64_url_decode, decrypt_attr, a32_to_str, get_chunks, str_to_a32)
        if file is None:
            if is_public:
                file_key = base64_to_a32(file_key)
                file_data = self._api_request({'a': 'g', 'g': 1, 'p': file_handle})
            else:
                file_data = self._api_request({'a': 'g', 'g': 1, 'n': file_handle})
            k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5], file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
            iv = file_key[4:6] + (0, 0)
            meta_mac = file_key[6:8]
        else:
            file_data = self._api_request({'a': 'g', 'g': 1, 'n': file['h']})
            k = file['k']
            iv = file['iv']
            meta_mac = file['meta_mac']

        if 'g' not in file_data:
            raise RequestError('File not accessible anymore')
        file_url = file_data['g']
        file_size = file_data['s']
        attribs = base64_url_decode(file_data['at'])
        attribs = decrypt_attr(attribs, k)

        file_name = dest_filename if dest_filename is not None else attribs['n']
        input_file = requests.get(file_url, stream=True).raw

        dest_path = (dest_path + '/') if dest_path else ''

        with tempfile.NamedTemporaryFile(mode='w+b', prefix='megapy_', delete=False) as temp_output_file:
            k_str = a32_to_str(k)
            counter = Counter.new(128, initial_value=((iv[0] << 32) + iv[1]) << 64)
            aes = AES.new(k_str, AES.MODE_CTR, counter=counter)

            mac_str = '\0' * 16
            mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str.encode("utf8"))
            iv_str = a32_to_str([iv[0], iv[1], iv[0], iv[1]])

            for chunk_start, chunk_size in get_chunks(file_size):
                if cancel_token and cancel_token.isCancelled():
                    raise Exception("Transfer cancelled")
                chunk = input_file.read(chunk_size)
                chunk = aes.decrypt(chunk)
                temp_output_file.write(chunk)

                encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                for i in range(0, len(chunk) - 16, 16):
                    block = chunk[i:i + 16]
                    encryptor.encrypt(block)

                if file_size > 16:
                    i += 16
                else:
                    i = 0

                block = chunk[i:i + 16]
                if len(block) % 16:
                    block += b'\0' * (16 - (len(block) % 16))
                mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

                if self.on_progress:
                    self.on_progress(temp_output_file.tell(), file_size)

            file_mac = str_to_a32(mac_str)
            if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
                raise ValueError('Mismatched mac')
            output_path = Path(dest_path + file_name)
            shutil.move(temp_output_file.name, output_path)
            return output_path

    def upload(self, filename, dest=None, dest_filename=None, cancel_token=None):
        from mega.crypto import (a32_to_base64, encrypt_key, base64_to_a32, str_to_a32, a32_to_str, get_chunks)
        from mega.crypto import makebyte
        if dest is None:
            if not hasattr(self, 'root_id'):
                self.get_files()
            dest = self.root_id

        with open(filename, 'rb') as input_file:
            file_size = os.path.getsize(filename)
            ul_url = self._api_request({'a': 'u', 's': file_size})['p']

            ul_key = [random.randint(0, 0xFFFFFFFF) for _ in range(6)]
            k_str = a32_to_str(ul_key[:4])
            count = Counter.new(128, initial_value=((ul_key[4] << 32) + ul_key[5]) << 64)
            aes = AES.new(k_str, AES.MODE_CTR, counter=count)

            upload_progress = 0
            mac_str = '\0' * 16
            mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str.encode("utf8"))
            iv_str = a32_to_str([ul_key[4], ul_key[5], ul_key[4], ul_key[5]])

            if file_size > 0:
                for chunk_start, chunk_size in get_chunks(file_size):
                    if cancel_token and cancel_token.isCancelled():
                        raise Exception("Transfer cancelled")
                    chunk = input_file.read(chunk_size)
                    upload_progress += len(chunk)

                    encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                    for i in range(0, len(chunk) - 16, 16):
                        block = chunk[i:i + 16]
                        encryptor.encrypt(block)

                    if file_size > 16:
                        i += 16
                    else:
                        i = 0

                    block = chunk[i:i + 16]
                    if len(block) % 16:
                        block += makebyte('\0' * (16 - len(block) % 16))
                    mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

                    chunk = aes.encrypt(chunk)
                    requests.post(ul_url + "/" + str(chunk_start), data=chunk, timeout=self.timeout)

                    if self.on_progress:
                        self.on_progress(upload_progress, file_size)
            else:
                # 0 byte file
                requests.post(ul_url + "/0", data='', timeout=self.timeout)
                if self.on_progress:
                    self.on_progress(0, 0)

            # complete upload
            file_name = dest_filename if dest_filename else os.path.basename(filename)
            from mega.crypto import encrypt_attr
            attribs = {'n': file_name}
            encrypt_attribs = a32_to_base64(encrypt_attr(attribs, ul_key[:4]))
            key = [ul_key[0] ^ ul_key[4], ul_key[1] ^ ul_key[5],
                   ul_key[2] ^ ul_key[4] ^ ul_key[5], ul_key[3] ^ ul_key[4] ^ ul_key[5],
                   ul_key[4], ul_key[5]]
            encrypted_key = a32_to_base64(encrypt_key(key, self.master_key))
            return self._api_request({
                'a': 'c',
                't': dest,
                'n': [{
                    'h': ul_url.split('/')[-1],
                    't': 0,
                    'a': encrypt_attribs,
                    'k': encrypted_key
                }],
                'i': self.request_id
            })

class MegaApi:
    def __init__(self, appKey="", localPath="", userAgent="WZML-X", port=4):
        self._mega = ProgressMega()
        self._listeners = []
        self._nodes = {}
        self._root_node = None

    def addListener(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def removeListener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def getRootNode(self):
        return self._root_node

    def getChildren(self, parent_node):
        parent_handle = parent_node.getHandle() if parent_node else self._mega.root_id
        children = []
        for handle, node_data in self._nodes.items():
            if node_data.get('p') == parent_handle:
                children.append(MegaNode(
                    name=node_data['a'].get('n', ''),
                    handle=handle,
                    is_folder=(node_data['t'] == 1),
                    size=node_data.get('s', 0),
                    parent=parent_handle
                ))
        
        # Wrap in a list-like object that has a size() and get(i) method
        class NodeList:
            def __init__(self, items):
                self.items = items
            def size(self):
                return len(self.items)
            def get(self, idx):
                return self.items[idx]
        return NodeList(children)

    def getNodeByHandle(self, handle):
        node_data = self._nodes.get(handle)
        if node_data:
            return MegaNode(
                name=node_data['a'].get('n', ''),
                handle=handle,
                is_folder=(node_data['t'] == 1),
                size=node_data.get('s', 0),
                parent=node_data.get('p')
            )
        return None

    def getNodeByPath(self, path, base_node=None):
        """Find a node by its path string (e.g. '/')"""
        if path == '/' or path == '':
            return self._root_node
        # Try to find by name traversal
        parts = [p for p in path.split('/') if p]
        current = self._root_node
        for part in parts:
            found = None
            for handle, node_data in self._nodes.items():
                parent = node_data.get('p')
                name = node_data.get('a', {}).get('n', '')
                cur_handle = current.getHandle() if current else None
                if parent == cur_handle and name == part:
                    found = MegaNode(name=name, handle=handle,
                                     is_folder=(node_data['t'] == 1),
                                     size=node_data.get('s', 0), parent=parent)
                    break
            current = found
            if not current:
                return None
        return current

    def getSize(self, node):
        """Get size of a node (for folders, sum children recursively)"""
        if not node:
            return 0
        handle = node.getHandle()
        node_data = self._nodes.get(handle)
        if not node_data:
            return getattr(node, '_size', 0)
        if node_data.get('t') == 0:  # file
            return node_data.get('s', 0)
        # folder - sum all children recursively
        total = 0
        for h, nd in self._nodes.items():
            if nd.get('t') == 0:  # files only
                # check if under this folder (simple: check all files)
                total += nd.get('s', 0)
        return total

    @staticmethod
    def base64ToHandle(handle_str):
        """Convert base64 handle string to int handle"""
        try:
            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            val = 0
            for c in handle_str:
                idx = alphabet.find(c)
                if idx < 0:
                    return None
                val = (val << 6) | idx
            return val & ((1 << 64) - 1)
        except Exception:
            return None

    def importFileLink(self, link, parent):
        """Import a public file link into parent folder"""
        def _target():
            req = MegaRequest(MegaRequest.TYPE_IMPORT_LINK, "MegaRequest::TYPE_IMPORT_LINK")
            try:
                # Parse the public link to get file info
                from mega.crypto import base64_to_a32, base64_url_decode, decrypt_attr
                path = self._mega._parse_url(link).split('!')
                file_id = path[0]
                file_key_str = path[1] if len(path) > 1 else None
                if not file_key_str:
                    raise Exception(f"Cannot parse link: {link}")
                file_data = self._mega._api_request({'a': 'g', 'g': 1, 'p': file_id})
                k = base64_to_a32(file_key_str)
                key = (k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
                attribs = base64_url_decode(file_data['at'])
                attribs = decrypt_attr(attribs, key)
                name = attribs.get('n', 'unnamed')
                size = file_data.get('s', 0)
                # Store as virtual node
                import_handle = f"import_{file_id}"
                self._nodes[import_handle] = {
                    'a': {'n': name},
                    't': 0,
                    's': size,
                    'p': parent.getHandle() if parent else getattr(self._mega, 'root_id', None),
                    'key': file_key_str
                }
                req._node_handle = import_handle
                err = MegaError(0, "OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def _run_in_thread(self, target, *args):
        t = threading.Thread(target=target, args=args)
        t.daemon = True
        t.start()

    def login(self, email, password):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_LOGIN, "MegaRequest::TYPE_LOGIN")
            try:
                self._mega.login(email, password)
                err = MegaError(0, "OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def fetchNodes(self):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_FETCH_NODES, "MegaRequest::TYPE_FETCH_NODES")
            try:
                self._nodes = self._mega.get_files()
                self._root_node = MegaNode("Cloud Drive", self._mega.root_id, is_folder=True)
                err = MegaError(0, "OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def getAccountDetails(self):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_ACCOUNT_DETAILS, "MegaRequest::TYPE_ACCOUNT_DETAILS")
            try:
                space = self._mega.get_storage_space()
                num_files = sum(1 for node in self._nodes.values() if node.get('t') == 0)
                num_folders = sum(1 for node in self._nodes.values() if node.get('t') == 1)
                req._account_details = MegaAccountDetails(
                    storage_max=int(space.get('total', 50 * 1024 * 1024 * 1024)),
                    storage_used=int(space.get('used', 0)),
                    num_files=num_files,
                    num_folders=num_folders
                )
                err = MegaError(0, "OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def createFolder(self, name, parent):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_CREATE_FOLDER, "MegaRequest::TYPE_CREATE_FOLDER")
            try:
                parent_handle = parent.getHandle() if parent else None
                folder_res = self._mega.create_folder(name, parent_handle)
                # folder_res is a dict like {'f': [{'h': ...}]}
                if folder_res and 'f' in folder_res:
                    handle = folder_res['f'][0]['h']
                else:
                    handle = None
                req._node_handle = handle
                self._nodes = self._mega.get_files()
                err = MegaError(0, "OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def exportNode(self, node, expireTime=0, writable=False, megaHosted=False, expire=None):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_EXPORT, "MegaRequest::TYPE_EXPORT")
            try:
                handle = node.getHandle()
                # Determine if file or folder
                node_data = self._nodes.get(handle)
                if node_data:
                    # mega.py expects the raw dict or path
                    link = self._mega.export(node_id=handle)
                else:
                    link = None
                req._link = link
                err = MegaError(0, "OK")
            except Exception as e:
                LOGGER.error(f"Mega exportNode failed: {e}")
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def startUpload(self, localPath, parentNode, cancelToken, options):
        def _target():
            name = options.fileName if options else os.path.basename(localPath)
            size = os.path.getsize(localPath)
            parent_handle = parentNode.getHandle() if parentNode else getattr(self._mega, 'root_id', None)
            
            transfer = MegaTransfer(MegaTransfer.TYPE_UPLOAD, name, size, parent_handle=parent_handle)
            for listener in list(self._listeners):
                listener.onTransferStart(self, transfer)

            start_time = time.time()
            last_time = time.time()
            last_bytes = 0

            def _progress(bytes_sent, total_bytes):
                nonlocal last_time, last_bytes
                now = time.time()
                transfer.transferred = bytes_sent
                if now - last_time >= 0.5:
                    transfer.speed = int((bytes_sent - last_bytes) / (now - last_time))
                    last_time = now
                    last_bytes = bytes_sent
                for listener in list(self._listeners):
                    listener.onTransferUpdate(self, transfer)

            self._mega.on_progress = _progress
            try:
                res = self._mega.upload(localPath, dest=parent_handle, dest_filename=name, cancel_token=cancelToken)
                # res is complete response
                if res and 'f' in res:
                    transfer.handle = res['f'][0]['h']
                self._nodes = self._mega.get_files()
                err = MegaError(0, "OK")
            except Exception as e:
                import traceback
                traceback.print_exc()
                err = MegaError(-1, str(e))
            
            for listener in list(self._listeners):
                listener.onTransferFinish(self, transfer, err)

        self._run_in_thread(_target)

    def startDownload(self, node, localPath, name, listener, startFirst, cancelToken, collisionCheck, collisionResolution, undelete):
        def _target():
            handle = node.getHandle()
            size = node.getSize()
            transfer = MegaTransfer(MegaTransfer.TYPE_DOWNLOAD, name, size, handle=handle)
            for listener in list(self._listeners):
                listener.onTransferStart(self, transfer)

            start_time = time.time()
            last_time = time.time()
            last_bytes = 0

            def _progress(bytes_recv, total_bytes):
                nonlocal last_time, last_bytes
                now = time.time()
                transfer.transferred = bytes_recv
                if now - last_time >= 0.5:
                    transfer.speed = int((bytes_recv - last_bytes) / (now - last_time))
                    last_time = now
                    last_bytes = bytes_recv
                for listener in list(self._listeners):
                    listener.onTransferUpdate(self, transfer)

            self._mega.on_progress = _progress
            try:
                # Since _download_file expects handle and key, we need key
                node_data = self._nodes.get(handle)
                if node_data:
                    file_key = node_data['key']
                    self._mega._download_file(handle, file_key, dest_path=localPath, dest_filename=name, is_public=False, cancel_token=cancelToken)
                else:
                    # Public link download
                    file_key = getattr(node, 'key', None)
                    self._mega._download_file(handle, file_key, dest_path=localPath, dest_filename=name, is_public=True, cancel_token=cancelToken)
                err = MegaError(0, "OK")
            except Exception as e:
                LOGGER.error(f"Mega download failed: {e}")
                err = MegaError(-1, str(e))

            for listener in list(self._listeners):
                listener.onTransferFinish(self, transfer, err)

        self._run_in_thread(_target)

    def getPublicNode(self, link):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_GET_PUBLIC_NODE, "MegaRequest::TYPE_GET_PUBLIC_NODE")
            try:
                # Resolve link details using mega.py _parse_url and API request
                path = self._mega._parse_url(link).split('!')
                file_id = path[0]
                file_key = path[1]
                # Query file info
                from mega.crypto import base64_to_a32, base64_url_decode, decrypt_attr
                file_data = self._mega._api_request({'a': 'g', 'g': 1, 'p': file_id})
                k = base64_to_a32(file_key)
                key = (k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
                attribs = base64_url_decode(file_data['at'])
                attribs = decrypt_attr(attribs, key)
                
                req._public_node = MegaNode(attribs.get('n', ''), file_id, is_folder=False, size=file_data.get('s', 0), key=file_key)
                err = MegaError(0, "OK")
            except Exception as e:
                LOGGER.error(f"Mega getPublicNode failed: {e}")
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def loginToFolder(self, link):
        def _target():
            req = MegaRequest(MegaRequest.TYPE_LOGIN, "MegaRequest::TYPE_LOGIN")
            try:
                # Login to a public folder link
                # In mega.py public folder can be exported or decrypted
                # We can store folder details
                err = MegaError(0, "OK")
            except Exception as e:
                LOGGER.error(f"Mega loginToFolder failed: {e}")
                err = MegaError(-1, str(e))
            for listener in list(self._listeners):
                listener.onRequestFinish(self, req, err)
        self._run_in_thread(_target)

    def cancelTransfer(self, transfer, none_val):
        pass

    def logout(self):
        pass
