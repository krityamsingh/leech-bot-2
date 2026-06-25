import sys
import os
import time

print("Importing mega from local package...")
from mega import MegaApi, MegaRequest, MegaListener, MegaUploadOptions

class TestListener(MegaListener):
    def __init__(self):
        self.login_done = False
        self.fetch_done = False
        self.create_done = False
        self.upload_done = False
        self.export_done = False
        self.uploaded_node = None
        self.folder_node = None
        self.link = None

    def onRequestFinish(self, api, request, error):
        req_type = request.getType()
        print(f"Request Finished: {req_type}, Error: {error.getErrorCode()} - {error.toString()}")
        if req_type == MegaRequest.TYPE_LOGIN:
            self.login_done = True
        elif req_type == MegaRequest.TYPE_FETCH_NODES:
            self.fetch_done = True
        elif req_type == MegaRequest.TYPE_CREATE_FOLDER:
            self.create_done = True
            self.folder_node = api.getNodeByHandle(request.getNodeHandle())
        elif req_type == MegaRequest.TYPE_EXPORT:
            self.export_done = True
            self.link = request.getLink()

    def onTransferStart(self, api, transfer):
        print(f"Transfer Started: {transfer.getFileName()} ({transfer.getTotalBytes()} bytes)")

    def onTransferUpdate(self, api, transfer):
        print(f"Transfer Progress: {transfer.getTransferredBytes()}/{transfer.getTotalBytes()} bytes, Speed: {transfer.getSpeed()} B/s")

    def onTransferFinish(self, api, transfer, error):
        print(f"Transfer Finished: {transfer.getFileName()}, Error: {error.getErrorCode()}")
        self.upload_done = True
        if error.getErrorCode() == 0:
            # Refresh nodes to get the uploaded node
            api._nodes = api._mega.get_files()
            self.uploaded_node = api.getNodeByHandle(transfer.getNodeHandle())

api = MegaApi()
listener = TestListener()
api.addListener(listener)

print("Starting login...")
api.login("monafey798@luxudata.com", "krityam1234")
for _ in range(15):
    if listener.login_done: break
    time.sleep(1)

print("Starting fetchNodes...")
api.fetchNodes()
for _ in range(15):
    if listener.fetch_done: break
    time.sleep(1)

print("Creating test folder...")
api.createFolder("wz_test_folder", api.getRootNode())
for _ in range(15):
    if listener.create_done: break
    time.sleep(1)

print("Created folder:", listener.folder_node.getName() if listener.folder_node else "None")

# Write a small file to upload
with open("test_upload.txt", "w") as f:
    f.write("Hello from WZ Bot shim test!")

print("Uploading file...")
opts = MegaUploadOptions()
opts.fileName = "test_upload.txt"
api.startUpload("test_upload.txt", listener.folder_node, None, opts)
for _ in range(30):
    if listener.upload_done: break
    time.sleep(1)

if os.path.exists("test_upload.txt"):
    os.remove("test_upload.txt")

print("Uploaded node:", listener.uploaded_node.getName() if listener.uploaded_node else "None")

if listener.uploaded_node:
    print("Exporting node (getting public link)...")
    api.exportNode(listener.uploaded_node)
    for _ in range(15):
        if listener.export_done: break
        time.sleep(1)
    print("Exported Link:", listener.link)
