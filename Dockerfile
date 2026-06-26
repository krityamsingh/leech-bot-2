FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app

# ── Required credentials ───────────────────────────────────────────────────────
# NOTE: BOT_TOKEN intentionally NOT set here — Railway provides it per-deployment.
# Everything else lives in this Dockerfile so Railway only needs BOT_TOKEN.
ENV TELEGRAM_API=26676741 \
    TELEGRAM_HASH=6fbc29f23c15bdb0c7fbbefe65c9193a \
    OWNER_ID=6118760915 \
    CMD_SUFFIX=3 \
    USER_SESSION_STRING=BQGXDgUAjADJk0-Tki-dkPdlU3J90KUGoDSiTX71r_C7zfUMY0CeQDZn29u7rQML-ZA1QGm1ZUIAKryKvcMxaijXJMmHya4W2K0hw3glXFzwsx_DUgFeOJxgBg39op8luPxhVuBlPbYd1929tMKn7pZO8HaNWx2ka4m75lFJDUDEITSguiWqm8Yc6Kn_hSnTJAQOhottfPND8mCRUtD-1_piKoajzBjKbKl2epA0LE-gwS83tzehhCO1_ybi1fEh9gGc8w_THUlNu5fPNdrzyO1dugV6Q2x67Z4B-1hIYDoG6WUu9kbLlpZu1Ue4RN9xjWjvUxmuTmEsaHjUgXP6vLgeNSVnCAAAAAGGIOrzAA

# ── Helper clients ─────────────────────────────────────────────────────────────
# HELPER_TOKENS: space-separated bot tokens -- add each bot as admin to LEECH_DUMP_CHAT
ENV HELPER_TOKENS=8694415781:AAGMjpQQf8RbmRgd8sbTccok4dSdXje6CYA
# HELPER_STRINGS: uncomment and add user session strings as you generate them
# One string per line, separated by a space or \n
# ENV HELPER_STRINGS=BQG...session2... BQG...session3...

# ── HyperTG speed settings ─────────────────────────────────────────────────────
# HYPER_THREADS=0 = auto-tune to CPU cores
# HYPER_PIPELINE=64 (in-flight requests per client). 128/256 can OOM on small RAM.
# HYPER_CHUNK=1MB = MTProto standard media chunk.
ENV USE_HYPER=true \
    HYPER_THREADS=0 \
    HYPER_PIPELINE=64 \
    HYPER_CHUNK=1048576

# ── Upload/transmission settings ───────────────────────────────────────────────
ENV TRANSMISSION_MODE=both \
    LEECH_DUMP_CHAT=-1003864293232 \
    LEECH_SPLIT_SIZE=2097152000

# ── Upload destination ────────────────────────────────────────────────────────
ENV DOWNLOAD_DIR=/usr/src/app/downloads/ \
    DEFAULT_UPLOAD=gd \
    GDRIVE_ID=1t4m29Fd78WTgLFIh_PXoUTjjOKcO-kZ5 \
    IS_TEAM_DRIVE=true \
    DRIVE_CATEGORY_SA=anitasingh191975@gmail.com \
    USE_SERVICE_ACCOUNTS=false \
    STOP_DUPLICATE=true

# ── Branding ──────────────────────────────────────────────────────────────────
ENV AUTHOR_NAME=WZML-X \
    AUTHOR_URL=https://t.me/Unrealrajput

# ── Bot behaviour ─────────────────────────────────────────────────────────────
ENV BOT_PM=true \
    SET_COMMANDS=true \
    MEDIA_GROUP=true \
    AS_DOCUMENT=false \
    STATUS_UPDATE_INTERVAL=15 \
    STATUS_LIMIT=10 \
    TIMEZONE=Asia/Kolkata

# ── Disabled services ─────────────────────────────────────────────────────────
ENV DISABLE_JD=true \
    DISABLE_NZB=true \
    DISABLE_MEGA=false \
    DISABLE_TORRENTS=true \
    DISABLE_LEECH=false \
    DISABLE_YTDLP=false

# ── Deploy ────────────────────────────────────────────────────────────────────
ENV RUN_UPDATE_ON_START=false \
    UPSTREAM_REPO=https://github.com/krityamsingh/leach-bot \
    UPSTREAM_BRANCH=wzv3

COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /usr/src/app/downloads

ENTRYPOINT ["bash", "start.sh"]
