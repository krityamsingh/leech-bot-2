FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app

# ── Required credentials baked into image ─────────────────────────────────────
ENV BOT_TOKEN=8774145303:AAESuoxl9COf15MaIOi7pBvUBGeW6Jg6Dvk \
    TELEGRAM_API=26676741 \
    TELEGRAM_HASH=6fbc29f23c15bdb0c7fbbefe65c9193a \
    OWNER_ID=6118760915 \
    USER_SESSION_STRING=1BVtsOH4BuzNOuNpi4YmIncBS-lELWa3q_SQ4GBUqB6r80fBkVxHnx9Li39qkQqExWO754iSBkAAUUtXf_IAzvs1cU9BB14IT6pLr-NhthQSLGZV5_ln7JmkOSq8ge4Q_kml873LwYAobnISeWrqD1of6QQzOZ5mrLtQG-UxzdXf9ceASbG35kwQOJKmSSYupMJBAnAwA9F8WjGXWg1BoF0AT0VXHkqzvdumIgRZ4Ca2mNFn8-n5cPZCTeP--4zAOe7eLOBbYkX6xlzYtTT2TMy7i6u1LK-gTIves6J6vp7cOAkr54bn8JUyXsUaH2AcoMVR-Tm99KHC_2E6MRM7zYytg4Hz8u0Y=

# ── Helper bot for Hyper TG upload ────────────────────────────────────────────
ENV HELPER_TOKENS=8694415781:AAGMjpQQf8RbmRgd8sbTccok4dSdXje6CYA \
    USE_HYPER=true \
    HYPER_THREADS=64

# ── Upload settings ───────────────────────────────────────────────────────────
ENV DOWNLOAD_DIR=/usr/src/app/downloads/ \
    DEFAULT_UPLOAD=gd \
    GDRIVE_ID=1t4m29Fd78WTgLFIh_PXoUTjjOKcO-kZ5 \
    IS_TEAM_DRIVE=true \
    DRIVE_CATEGORY_SA=anitasingh191975@gmail.com \
    USE_SERVICE_ACCOUNTS=false \
    STOP_DUPLICATE=true \
    LEECH_DUMP_CHAT=-1003864293232

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

# ── Disable services not available on Railway ─────────────────────────────────
ENV DISABLE_JD=true \
    DISABLE_NZB=true \
    DISABLE_MEGA=false \
    DISABLE_TORRENTS=true \
    DISABLE_LEECH=false \
    DISABLE_YTDLP=false

# ── Deploy settings ───────────────────────────────────────────────────────────
ENV RUN_UPDATE_ON_START=false \
    UPSTREAM_REPO=https://github.com/krityamsingh/leach-bot \
    UPSTREAM_BRANCH=wzv3

COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

COPY . .

# Ensure downloads dir exists inside image
RUN mkdir -p /usr/src/app/downloads

ENTRYPOINT ["bash", "start.sh"]
