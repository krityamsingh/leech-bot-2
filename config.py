# ─────────────────────────────────────────────────────────────────────────────
# Zoro Leech Bot — full config (single source of truth)
# Railway only needs BOT_TOKEN. Everything else lives in this file.
# ─────────────────────────────────────────────────────────────────────────────

# ── REQUIRED CREDENTIALS ─────────────────────────────────────────────────────
# Hardcoded for this deployment. A Railway env var BOT_TOKEN (if set) still
# takes precedence via Config.load_env().
BOT_TOKEN = "8643615014:AAFRhgZ9lOTzoq53nfQt3yPqaGDxDQlkjDE"
OWNER_ID = 6118760915
TELEGRAM_API = 26676741
TELEGRAM_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"

# ── PERSISTENT STORAGE ───────────────────────────────────────────────────────
DATABASE_URL = "mongodb+srv://pabitrabarman0002:rajrajkumar02@rajrajkumar.rrwa7zy.mongodb.net/?retryWrites=true&w=majority&appName=Rajrajkumar"
DOWNLOAD_DIR = "/usr/src/app/downloads/"

# ── COMMAND ROUTING ──────────────────────────────────────────────────────────
CMD_SUFFIX = "3"                # /l3, /m3, /us3, /h3, /speedtest3, ...
AUTHORIZED_CHATS = ""
SUDO_USERS = ""
DEFAULT_LANG = "en"

# ── USER + HELPER CLIENTS (the speed lever) ──────────────────────────────────
# "Leech" user session — admin in LEECH_DUMP_CHAT (verified).
USER_SESSION_STRING = "BQGXDgUAjADJk0-Tki-dkPdlU3J90KUGoDSiTX71r_C7zfUMY0CeQDZn29u7rQML-ZA1QGm1ZUIAKryKvcMxaijXJMmHya4W2K0hw3glXFzwsx_DUgFeOJxgBg39op8luPxhVuBlPbYd1929tMKn7pZO8HaNWx2ka4m75lFJDUDEITSguiWqm8Yc6Kn_hSnTJAQOhottfPND8mCRUtD-1_piKoajzBjKbKl2epA0LE-gwS83tzehhCO1_ybi1fEh9gGc8w_THUlNu5fPNdrzyO1dugV6Q2x67Z4B-1hIYDoG6WUu9kbLlpZu1Ue4RN9xjWjvUxmuTmEsaHjUgXP6vLgeNSVnCAAAAAGGIOrzAA"
# Helper bot tokens (space-separated). 17 unique bots — add EACH as admin to
# LEECH_DUMP_CHAT so they can see/download the files. Each bot adds a parallel
# download lane (~2-5 MB/s) via the HyperDL coordinator.
HELPER_TOKENS = "8980935526:AAHelJTsJc8b-LcHLbFkw8OjcDBlKMkzw2k 8753165289:AAFuwaSgKtckYR2VyHXEZwhJJiQsFcoKXeA 8949216879:AAFait-J7gbedx5DZlpHN1LmJncC1UkSxy0 8293232943:AAHO9K2bnxWUEeMnWIEsx9HEl9-6CFT6qgw 8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk 8382794975:AAF70jE5DWLGr9OGPK3OZH8MUCZovyRGZ1A 8749817037:AAEYJ1W6zjvnI34iOiQZAXkd5kTJgy8KtMA 8639417912:AAG3FYUQ573HGaLPPGU7srgUbhQAWD4Y7Gg 8837189677:AAE9T8RhTXxagL12JQ405bqQ0VtGPzx_I5A 8392938925:AAEGGgRsP5_FsICwk70rhPCPsi_D6dJkFF8 8260866955:AAFyZ2LyG7tmHkOzDBXoZkx8sgcx1U3d7dE 8201403619:AAHKrHizJ6YuwYcT5usaBagFEfUR0r-SzNc 8271548044:AAGQyjjVwPCiX1f79zzypCFS9BOZDDDRCps 7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY 8511156627:AAGERpBUl7edSj7toGJBMh8V-b7EvtRCfIY 8597691736:AAGU7Yl_tonzLZeINMcklPKKcMdJYLgVTkQ 8808349957:AAHup2bMinFD95PV1idFkNwi2erI9nIdu-M"
# Helper USER session strings (space-separated). Each one ≈ +3-5 MB/s upload.
HELPER_STRINGS = ""

# ── HYPER TELEGRAM TRANSFER ──────────────────────────────────────────────────
USE_HYPER = True
HYPER_THREADS = 64              # 0 = auto. 64 = explicitly max parallel workers per upload
HYPER_PIPELINE = 128            # in-flight requests per client (MTProto window) — raised for instant max speed
HYPER_CHUNK = 1024 * 1024       # 1 MB = standard MTProto media chunk

# ── PHP / MadelineProto BRIDGE (optional) ────────────────────────────────────
# When True, the bot delegates EACH leech upload/download to the PHP
# MadelineProto microservice running at PHP_BRIDGE_URL (default
# http://127.0.0.1:9090). On any failure (service down, error response,
# 3 consecutive timeouts → circuit breaker) the bot transparently falls
# back to Kurigram HyperUP/HyperDL — your leech never breaks.
#
# To enable end-to-end:
#   1. Flip this flag to True
#   2. Add a Railway Persistent Volume mounted at /usr/src/app/php-bridge/data
#      (otherwise session is wiped on every redeploy)
#   3. SSH into the Railway container: `cd /usr/src/app/php-bridge && php login.php`
#   4. Restart the service
USE_PHP_TRANSPORT = False
PHP_BRIDGE_URL = "http://127.0.0.1:9090"

# ── TRANSMISSION + LEECH ─────────────────────────────────────────────────────
TRANSMISSION_MODE = "both"      # "user" | "bot" | "both" (hybrid)
LEECH_DUMP_CHAT = "-1003864293232"
LEECH_SPLIT_SIZE = 0            # 0 = auto (Telegram limit)
LEECH_PREFIX = ""
LEECH_SUFFIX = ""
LEECH_FONT = ""
LEECH_CAPTION = ""
THUMBNAIL_LAYOUT = ""
AS_DOCUMENT = False             # False = upload videos AS video, not raw file
MEDIA_GROUP = True              # group split parts together in Telegram
EQUAL_SPLITS = False

# ── BOT BEHAVIOUR ────────────────────────────────────────────────────────────
BOT_PM = True
SET_COMMANDS = True
DELETE_LINKS = False
SOURCE_LINK = False
COLORED_BTNS = True
MEDIA_STORE = True
CLEAN_LOG_MSG = False
STATUS_LIMIT = 10
STATUS_UPDATE_INTERVAL = 15
INC_TASK_NOTIFY = False
EXCLUDED_EXTENSIONS = ""
YT_DLP_OPTIONS = {}
NAME_SWAP = ""
FFMPEG_CMDS = {}
UPLOAD_PATHS = {}
WEB_ACCESS_PASSWORD = ""

# ── FEATURE TOGGLES (kept from previous deployment) ──────────────────────────
DISABLE_TORRENTS = True
DISABLE_LEECH = False
DISABLE_BULK = False
DISABLE_MULTI = False
DISABLE_SEED = False
DISABLE_FF_MODE = False
DISABLE_MEGA = False
DISABLE_JD = True
DISABLE_NZB = True
DISABLE_RSS = False
DISABLE_SEARCH = False
DISABLE_YTDLP = False

# ── TASK LIMITS (0 = unlimited) ──────────────────────────────────────────────
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
BOT_MAX_TASKS = 0
USER_MAX_TASKS = 0
USER_TIME_INTERVAL = 0

# ── UPLOAD DESTINATION ───────────────────────────────────────────────────────
DEFAULT_UPLOAD = "gd"

# ── GOOGLE DRIVE ─────────────────────────────────────────────────────────────
GDRIVE_ID = "1t4m29Fd78WTgLFIh_PXoUTjjOKcO-kZ5"
GD_DESP = "Uploaded via Mirror Bot"
DRIVE_CATEGORY_SA = "anitasingh191975@gmail.com"
IS_TEAM_DRIVE = True
STOP_DUPLICATE = True
INDEX_URL = ""
USE_SERVICE_ACCOUNTS = False

# ── RCLONE ───────────────────────────────────────────────────────────────────
RCLONE_PATH = ""
RCLONE_FLAGS = ""
RCLONE_SERVE_URL = ""
SHOW_CLOUD_LINK = True
RCLONE_SERVE_PORT = 0
RCLONE_SERVE_USER = ""
RCLONE_SERVE_PASS = ""

# ── MEGA ─────────────────────────────────────────────────────────────────────
MEGA_EMAIL = "monafey798@luxudata.com"
MEGA_PASSWORD = "krityam1234"

# ── JDOWNLOADER (disabled but kept for re-enable) ────────────────────────────
JD_EMAIL = "monafey798@luxudata.com"
JD_PASS = "krityam"

# ── SABNZBD / USENET (disabled) ──────────────────────────────────────────────
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

# ── LOG CHANNELS ─────────────────────────────────────────────────────────────
LINKS_LOG_ID = ""
MIRROR_LOG_ID = ""

# ── TELEGRAPH ────────────────────────────────────────────────────────────────
AUTHOR_NAME = "WZML-X"
AUTHOR_URL = "https://t.me/Unrealrajput"

# ── WEB / QBITTORRENT ────────────────────────────────────────────────────────
BASE_URL = ""
WEB_PINCODE = True
TORRENT_TIMEOUT = 0

# ── QUEUEING ─────────────────────────────────────────────────────────────────
QUEUE_ALL = 0
QUEUE_DOWNLOAD = 0
QUEUE_UPLOAD = 0

# ── RSS ──────────────────────────────────────────────────────────────────────
RSS_DELAY = 600
RSS_CHAT = ""
RSS_SIZE_LIMIT = 0

# ── TORRENT SEARCH (kept for future use) ─────────────────────────────────────
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

# ── YT-DLP / YOUTUBE ─────────────────────────────────────────────────────────
YT_DESP = "Uploaded with WZ Bot"
YT_TAGS = ["telegram", "bot", "youtube"]
YT_CATEGORY_ID = 22
YT_PRIVACY_STATUS = "unlisted"

# ── UPDATE / TIMEZONE ────────────────────────────────────────────────────────
UPSTREAM_REPO = ""
UPSTREAM_BRANCH = "master"
TIMEZONE = "Asia/Kolkata"
