# Stub for wz_bin - maps to real system binaries
_BINS = ["aria2c", "qbittorrent-nox", "ffmpeg", "rclone", "sabnzbd-server"]


def bin_name(index):
    return _BINS[index] if index < len(_BINS) else ""
