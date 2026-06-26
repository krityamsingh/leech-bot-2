FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app

# All configuration lives in config.py (single source of truth).
# Railway only needs to set BOT_TOKEN as an env var.

COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /usr/src/app/downloads

ENTRYPOINT ["bash", "start.sh"]
