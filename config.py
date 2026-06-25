# ── REQUIRED CONFIG ───────────────────────────────────────────────────────────
BOT_TOKEN = "8774145303:AAESuoxl9COf15MaIOi7pBvUBGeW6Jg6Dvk"
OWNER_ID = 6118760915
TELEGRAM_API = 26676741
TELEGRAM_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
DATABASE_URL = ""
DOWNLOAD_DIR = "/home/ironman2711/Desktop/leach-bot/downloads/"

# ── OPTIONAL CONFIG ───────────────────────────────────────────────────────────
DEFAULT_LANG = "en"
USER_SESSION_STRING = "BQGXDgUAjADJk0-Tki-dkPdlU3J90KUGoDSiTX71r_C7zfUMY0CeQDZn29u7rQML-ZA1QGm1ZUIAKryKvcMxaijXJMmHya4W2K0hw3glXFzwsx_DUgFeOJxgBg39op8luPxhVuBlPbYd1929tMKn7pZO8HaNWx2ka4m75lFJDUDEITSguiWqm8Yc6Kn_hSnTJAQOhottfPND8mCRUtD-1_piKoajzBjKbKl2epA0LE-gwS83tzehhCO1_ybi1fEh9gGc8w_THUlNu5fPNdrzyO1dugV6Q2x67Z4B-1hIYDoG6WUu9kbLlpZu1Ue4RN9xjWjvUxmuTmEsaHjUgXP6vLgeNSVnCAAAAAGGIOrzAA"
CMD_SUFFIX = "1"
AUTHORIZED_CHATS = ""
SUDO_USERS = ""
STATUS_LIMIT = 10
STATUS_UPDATE_INTERVAL = 15
EXCLUDED_EXTENSIONS = ""
INC_TASK_NOTIFY = False
YT_DLP_OPTIONS = {}
NAME_SWAP = ""
FFMPEG_CMDS = {}
UPLOAD_PATHS = {}
WEB_ACCESS_PASSWORD = ""

# ── Hyper Telegram Downloader / Uploader ─────────────────────────────────────
HELPER_TOKENS = "8694415781:AAGMjpQQf8RbmRgd8sbTccok4dSdXje6CYA"          # Add extra bot tokens here for parallel TG uploads
USE_HYPER = True            # Enable multi-threaded Telegram upload/download
HYPER_THREADS = 64          # Number of parallel upload/download workers (Default: 64)
HYPER_PIPELINE = 32          # Concurrent requests per worker (Default: 32)
HYPER_CHUNK = 512 * 1024    # Working chunk size (Default: 512KB)

# ── Upload Destination ────────────────────────────────────────────────────────
DEFAULT_UPLOAD = "gd"        # "gd" = Google Drive (all /mirror commands go to Drive)

# ── Google Drive ──────────────────────────────────────────────────────────────
GDRIVE_ID = "1t4m29Fd78WTgLFIh_PXoUTjjOKcO-kZ5"   # Your 5TB drive folder ID
GD_DESP = "Uploaded via Mirror Bot"
DRIVE_CATEGORY_SA = "anitasingh191975@gmail.com"
IS_TEAM_DRIVE = True         # ← REQUIRED for shared/5TB drives (Shared Drive)
STOP_DUPLICATE = True        # Skip re-uploading files already in Drive
INDEX_URL = ""               # Leave blank unless you have an Index server
USE_SERVICE_ACCOUNTS = False # Using OAuth token.pickle (not SA)

# ── Rclone ────────────────────────────────────────────────────────────────────
RCLONE_PATH = ""
RCLONE_FLAGS = ""
RCLONE_SERVE_URL = ""
SHOW_CLOUD_LINK = True
RCLONE_SERVE_PORT = 0
RCLONE_SERVE_USER = ""
RCLONE_SERVE_PASS = ""

# ── Mega ──────────────────────────────────────────────────────────────────────
MEGA_EMAIL = "monafey798@luxudata.com"
MEGA_PASSWORD = "krityam1234"

# ── JDownloader ───────────────────────────────────────────────────────────────
JD_EMAIL = "monafey798@luxudata.com"
JD_PASS = "krityam"

# ── Sabnzbd (NZB) ─────────────────────────────────────────────────────────────
USENET_SERVERS = [
    {
        "name": "main",
        "host": "",
        "port": 563,
        "timeout": 60,
        "username": "",
        "password": "",
        "connections": 8,
        "ssl": 1,
        "ssl_verify": 2,
        "ssl_ciphers": "",
        "enable": 1,
        "required": 0,
        "optional": 0,
        "retention": 0,
        "send_group": 0,
        "priority": 0,
    }
]

# ── Enable / Disable Features ─────────────────────────────────────────────────
DISABLE_TORRENTS = False
DISABLE_LEECH = False
DISABLE_BULK = False
DISABLE_MULTI = False
DISABLE_SEED = False
DISABLE_FF_MODE = False
DISABLE_MEGA = False        # ← was True, now enabled
DISABLE_JD = False          # ← was True, now enabled
DISABLE_NZB = False         # ← was True, now enabled
DISABLE_RSS = False
DISABLE_SEARCH = False
DISABLE_YTDLP = False

# ── Leech Settings ────────────────────────────────────────────────────────────
LEECH_SPLIT_SIZE = 0         # 0 = auto (Telegram limit)
AS_DOCUMENT = False           # False = upload videos AS video (not raw file)
EQUAL_SPLITS = False
MEDIA_GROUP = True            # Group split parts together in Telegram
TRANSMISSION_MODE = "both"
LEECH_PREFIX = ""
LEECH_SUFFIX = ""
LEECH_FONT = ""
LEECH_CAPTION = ""
THUMBNAIL_LAYOUT = ""

# ── Log Channels ──────────────────────────────────────────────────────────────
LEECH_DUMP_CHAT = "-1003864293232"
LINKS_LOG_ID = ""
MIRROR_LOG_ID = ""

# ── Telegraph ─────────────────────────────────────────────────────────────────
AUTHOR_NAME = "WZML-X"
AUTHOR_URL = "https://t.me/Unrealrajput"

# ── Task Limits (0 = unlimited) ───────────────────────────────────────────────
DIRECT_LIMIT = 0
MEGA_LIMIT = 0
TORRENT_LIMIT = 0
YTDLP_LIMIT = 0
CLONE_LIMIT = 0
GDRIVE_LIMIT = 0
GD_DL_LIMIT = 0
RC_DL_LIMIT = 0
JD_LIMIT = 0
NZB_LIMIT = 0
PLAYLIST_LIMIT = 0
LEECH_LIMIT = 0
EXTRACT_LIMIT = 0
ARCHIVE_LIMIT = 0
STORAGE_LIMIT = 0

# ── Bot Settings ──────────────────────────────────────────────────────────────
BOT_PM = False
SET_COMMANDS = True
AS_DOCUMENT = False
EQUAL_SPLITS = False
MEDIA_GROUP = False
DELETE_LINKS = False
SOURCE_LINK = False
COLORED_BTNS = True
MEDIA_STORE = True
CLEAN_LOG_MSG = False
BOT_MAX_TASKS = 0
USER_MAX_TASKS = 0
USER_TIME_INTERVAL = 0

# ── Web / qBittorrent ─────────────────────────────────────────────────────────
BASE_URL = ""
WEB_PINCODE = True
TORRENT_TIMEOUT = 0

# ── Queueing ──────────────────────────────────────────────────────────────────
QUEUE_ALL = 0
QUEUE_DOWNLOAD = 0
QUEUE_UPLOAD = 0

# ── RSS ───────────────────────────────────────────────────────────────────────
RSS_DELAY = 600
RSS_CHAT = ""
RSS_SIZE_LIMIT = 0

# ── Torrent Search ────────────────────────────────────────────────────────────
SEARCH_API_LINK = ""
SEARCH_LIMIT = 0
SEARCH_PLUGINS = [
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/piratebay.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/limetorrents.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torlock.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentscsv.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/eztv.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentproject.py",
]

# ── YT-DLP / YouTube ──────────────────────────────────────────────────────────
YT_DESP = "Uploaded with WZ Bot"
YT_TAGS = ["telegram", "bot", "youtube"]
YT_CATEGORY_ID = 22
YT_PRIVACY_STATUS = "unlisted"

# ── Update ────────────────────────────────────────────────────────────────────
UPSTREAM_REPO = ""
UPSTREAM_BRANCH = "master"

# ── Timezone ──────────────────────────────────────────────────────────────────
TIMEZONE = "Asia/Kolkata"
