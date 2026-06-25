from asyncio import TimeoutError, create_subprocess_exec, gather, sleep
from asyncio.subprocess import DEVNULL, PIPE
from contextlib import suppress
from inspect import iscoroutinefunction
from pathlib import Path
from os import getcwd

from aioaria2 import Aria2WebsocketClient
from aiohttp import ClientError, ClientSession
from aioqbt.client import create_client
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .. import LOGGER, aria2_options
from .config_manager import BinConfig, Config

QBITTORRENT_API_URL = "http://127.0.0.1:8090/api/v2/"
QBITTORRENT_VERSION_URL = f"{QBITTORRENT_API_URL}app/version"


def wrap_with_retry(obj, max_retries=3):
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue

        attr = getattr(obj, attr_name)
        if iscoroutinefunction(attr):
            retry_policy = retry(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=5),
                retry=retry_if_exception_type(
                    (ClientError, TimeoutError, RuntimeError)
                ),
            )
            wrapped = retry_policy(attr)
            setattr(obj, attr_name, wrapped)
    return obj


async def _connect_aria2(retries=15, delay=2):
    from aioaria2.exceptions import Aria2rpcException

    for i in range(retries):
        try:
            return await Aria2WebsocketClient.new("http://localhost:6800/jsonrpc")
        except Aria2rpcException:
            if i == retries - 1:
                raise
            await sleep(delay)


async def _start_aria2_fallback():
    proc = await create_subprocess_exec(
        BinConfig.ARIA2_NAME,
        "--conf-path=configs/ac/ac.conf",
        "--daemon=true",
        "--rpc-listen-all=true",
        stdout=DEVNULL,
        stderr=PIPE,
    )
    await sleep(1)
    if proc.returncode is None or proc.returncode == 0:
        LOGGER.info("Aria2 fallback start requested.")
        return

    stderr = ""
    if proc.stderr:
        stderr = (await proc.stderr.read()).decode(errors="replace").strip()
    raise RuntimeError(f"Aria2 fallback start failed: {stderr}")


async def _wait_qbittorrent_ready(retries=10, delay=1):
    last_error = None
    for i in range(retries):
        try:
            async with ClientSession() as session:
                async with session.get(QBITTORRENT_VERSION_URL) as resp:
                    if resp.status < 500:
                        await resp.text()
                        return
                    last_error = RuntimeError(
                        f"qBittorrent Web API returned HTTP {resp.status}"
                    )
        except Exception as e:
            last_error = e
        if i != retries - 1:
            await sleep(delay)
    raise RuntimeError(
        f"qBittorrent Web API did not become ready at {QBITTORRENT_API_URL}: "
        f"{last_error}"
    )


async def _start_qbittorrent():
    proc = await create_subprocess_exec(
        BinConfig.QBIT_NAME,
        "-d",
        f"--profile={getcwd()}/configs/qbittorrent",
        stdout=DEVNULL,
        stderr=PIPE,
    )
    await sleep(1)
    if proc.returncode is None:
        LOGGER.info(f"qBittorrent start requested (PID: {proc.pid})")
        return

    stderr = ""
    if proc.stderr:
        stderr = (await proc.stderr.read()).decode(errors="replace").strip()

    if proc.returncode == 0:
        LOGGER.info(f"qBittorrent start requested (PID: {proc.pid})")
        return

    if "already running" in stderr.lower():
        LOGGER.info("qBittorrent is already running.")
        return

    raise RuntimeError(
        f"qBittorrent failed to start with code {proc.returncode}: {stderr}"
    )


class TorrentManager:
    aria2 = None
    qbittorrent = None

    @classmethod
    async def initiate(cls):
        if cls.aria2 and (Config.DISABLE_TORRENTS or cls.qbittorrent):
            return

        # ── Step 1: Aria2 (fatal — bot needs this) ───────────────────────────
        if not cls.aria2:
            try:
                try:
                    cls.aria2 = await _connect_aria2()
                except Exception:
                    LOGGER.warning("Aria2 is not ready, trying fallback start.")
                    await _start_aria2_fallback()
                    cls.aria2 = await _connect_aria2()
                LOGGER.info("Aria2 initialized successfully.")
            except Exception as e:
                LOGGER.error(f"Fatal: Aria2 failed to start: {e}")
                raise

        if Config.DISABLE_TORRENTS:
            LOGGER.info("Torrents are disabled. Skipping qBittorrent.")
            return

        # ── Step 2: qBittorrent (non-fatal — bot works without it) ───────────
        if not cls.qbittorrent:
            try:
                try:
                    await _wait_qbittorrent_ready(retries=1, delay=0)
                    LOGGER.info("Connected to existing qBittorrent Web API.")
                except Exception:
                    await _start_qbittorrent()
                    await _wait_qbittorrent_ready()

                cls.qbittorrent = await create_client(QBITTORRENT_API_URL)
                cls.qbittorrent = wrap_with_retry(cls.qbittorrent)
                LOGGER.info("qBittorrent initialized successfully.")
            except Exception as e:
                LOGGER.warning(
                    f"qBittorrent failed to start (bot will run without torrent support): {e}"
                )
                cls.qbittorrent = None

    @classmethod
    async def close_all(cls):
        close_tasks = []
        if cls.aria2:
            close_tasks.append(cls.aria2.close())
            cls.aria2 = None
        if cls.qbittorrent:
            close_tasks.append(cls.qbittorrent.close())
            cls.qbittorrent = None
        if close_tasks:
            await gather(*close_tasks)

    @classmethod
    async def aria2_remove(cls, download):
        if download.get("status", "") in ["active", "paused", "waiting"]:
            await cls.aria2.forceRemove(download.get("gid", ""))
        else:
            with suppress(Exception):
                await cls.aria2.removeDownloadResult(download.get("gid", ""))

    @classmethod
    async def remove_all(cls):
        await cls.pause_all()
        if cls.qbittorrent:
            await gather(
                cls.qbittorrent.torrents.delete("all", False),
                cls.aria2.purgeDownloadResult(),
            )
        else:
            await gather(
                cls.aria2.purgeDownloadResult(),
            )
        downloads = []
        results = await gather(cls.aria2.tellActive(), cls.aria2.tellWaiting(0, 1000))
        for res in results:
            downloads.extend(res)
        tasks = []
        tasks.extend(
            cls.aria2.forceRemove(download.get("gid")) for download in downloads
        )
        with suppress(Exception):
            await gather(*tasks)

    @classmethod
    async def overall_speed(cls):
        aria2_speed = await cls.aria2.getGlobalStat()
        download_speed = int(aria2_speed.get("downloadSpeed", "0"))
        upload_speed = int(aria2_speed.get("uploadSpeed", "0"))

        if cls.qbittorrent:
            qb_speed = await cls.qbittorrent.transfer.info()
            download_speed += qb_speed.dl_info_speed
            upload_speed += qb_speed.up_info_speed

        return download_speed, upload_speed

    @classmethod
    async def pause_all(cls):
        pause_tasks = [cls.aria2.forcePauseAll()]
        if cls.qbittorrent:
            pause_tasks.append(cls.qbittorrent.torrents.stop("all"))
        await gather(*pause_tasks)

    @classmethod
    async def change_aria2_option(cls, key, value):
        downloads = []
        results = await gather(cls.aria2.tellActive(), cls.aria2.tellWaiting(0, 1000))
        for res in results:
            downloads.extend(res)
        tasks = [
            cls.aria2.changeOption(download.get("gid"), {key: value})
            for download in downloads
            if download.get("status", "") != "complete"
        ]
        if tasks:
            try:
                await gather(*tasks)
            except Exception as e:
                LOGGER.error(e)
        if key not in ["checksum", "index-out", "out", "pause", "select-file"]:
            await cls.aria2.changeGlobalOption({key: value})
            aria2_options[key] = value


def aria2_name(download_info):
    if "bittorrent" in download_info and download_info["bittorrent"].get("info"):
        return download_info["bittorrent"]["info"]["name"]
    elif download_info.get("files"):
        if download_info["files"][0]["path"].startswith("[METADATA]"):
            return download_info["files"][0]["path"]
        file_path = download_info["files"][0]["path"]
        dir_path = download_info["dir"]
        if file_path.startswith(dir_path):
            return Path(file_path[len(dir_path) + 1 :]).parts[0]
        else:
            return ""
    else:
        return ""


def is_metadata(download_info):
    return any(
        f["path"].startswith("[METADATA]") for f in download_info.get("files", [])
    )
