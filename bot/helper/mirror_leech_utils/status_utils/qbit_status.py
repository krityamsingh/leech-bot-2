from asyncio import sleep, gather

from .... import LOGGER, qb_torrents, qb_listener_lock
from ....core.torrent_manager import TorrentManager
from ...ext_utils.status_utils import (
    MirrorStatus,
    EngineStatus,
    get_readable_file_size,
    get_readable_time,
)


async def get_download(tag, old_info=None):
    try:
        if not TorrentManager.qbittorrent:
            return old_info
        torrents = await TorrentManager.qbittorrent.torrents.info(tag=tag)
        if not torrents:
            return old_info
        res = torrents[0]
        return res or old_info
    except Exception as e:
        LOGGER.error(f"{e}: Qbittorrent, while getting torrent info. Tag: {tag}")
        return old_info


class QbittorrentStatus:
    def __init__(self, listener, seeding=False, queued=False):
        self.queued = queued
        self.seeding = seeding
        self.listener = listener
        self._info = None
        self.engine = EngineStatus().STATUS_QBIT

    async def update(self):
        self._info = await get_download(f"{self.listener.mid}", self._info)

    def _has_info(self):
        return self._info is not None

    def progress(self):
        if not self._has_info():
            return "0%"
        return f"{round(self._info.progress * 100, 2)}%"

    def processed_bytes(self):
        if not self._has_info():
            return get_readable_file_size(0)
        return get_readable_file_size(self._info.downloaded)

    def speed(self):
        if not self._has_info():
            return f"{get_readable_file_size(0)}/s"
        return f"{get_readable_file_size(self._info.dlspeed)}/s"

    def name(self):
        if not self._has_info():
            return self.listener.name
        if self._info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.listener.name}"
        else:
            return self.listener.name

    def size(self):
        if not self._has_info():
            return get_readable_file_size(self.listener.size)
        return get_readable_file_size(self._info.size)

    def eta(self):
        if not self._has_info():
            return "-"
        return get_readable_time(self._info.eta.total_seconds())

    async def status(self):
        await self.update()
        if not self._has_info():
            return MirrorStatus.STATUS_DOWNLOAD
        state = self._info.state
        if state == "queuedDL" or self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        elif state == "queuedUP":
            return MirrorStatus.STATUS_QUEUEUP
        elif state in ["stoppedDL", "stoppedUP"]:
            return MirrorStatus.STATUS_PAUSED
        elif state in ["checkingUP", "checkingDL"]:
            return MirrorStatus.STATUS_CHECK
        elif state in ["stalledUP", "uploading"] and self.seeding:
            return MirrorStatus.STATUS_SEED
        else:
            return MirrorStatus.STATUS_DOWNLOAD

    def seeders_num(self):
        if not self._has_info():
            return 0
        return self._info.num_seeds

    def leechers_num(self):
        if not self._has_info():
            return 0
        return self._info.num_leechs

    def uploaded_bytes(self):
        if not self._has_info():
            return get_readable_file_size(0)
        return get_readable_file_size(self._info.uploaded)

    def seed_speed(self):
        if not self._has_info():
            return f"{get_readable_file_size(0)}/s"
        return f"{get_readable_file_size(self._info.upspeed)}/s"

    def ratio(self):
        if not self._has_info():
            return "0"
        return f"{round(self._info.ratio, 3)}"

    def seeding_time(self):
        if not self._has_info():
            return "0s"
        return get_readable_time(int(self._info.seeding_time.total_seconds()))

    def task(self):
        return self

    def gid(self):
        if not self._has_info():
            return str(self.listener.mid)
        return self.hash()[:12]

    def hash(self):
        if not self._has_info():
            return str(self.listener.mid)
        return self._info.hash

    async def cancel_task(self):
        self.listener.is_cancelled = True
        await self.update()
        if not self._has_info():
            await self.listener.on_download_error("Torrent is no longer available!")
            return
        await TorrentManager.qbittorrent.torrents.stop([self._info.hash])
        if not self.seeding:
            tag = self._info.tags[0] if self._info.tags else str(self.listener.mid)
            if self.queued:
                LOGGER.info(f"Cancelling QueueDL: {self.name()}")
                msg = "task have been removed from queue/download"
            else:
                LOGGER.info(f"Cancelling Download: {self._info.name}")
                msg = "Stopped by user!"
            await sleep(0.3)
            await gather(
                self.listener.on_download_error(msg),
                TorrentManager.qbittorrent.torrents.delete([self._info.hash], True),
                TorrentManager.qbittorrent.torrents.delete_tags(
                    tags=[tag]
                ),
            )
            async with qb_listener_lock:
                if tag in qb_torrents:
                    del qb_torrents[tag]
