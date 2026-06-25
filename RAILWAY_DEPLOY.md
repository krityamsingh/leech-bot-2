# Railway Deployment

This repo is ready to deploy on Railway with Docker.

## Required Variables

Set these secrets in Railway service variables:

```env
BOT_TOKEN=
TELEGRAM_HASH=
DATABASE_URL=
```

`TELEGRAM_API`, `OWNER_ID`, `GDRIVE_ID`, and safe deploy defaults are baked into the Docker image and also listed in `railway.env.example`. You can still override them from Railway variables.

## Google Drive

The folder `1t4m29Fd78WTgLFIh_PXoUTjjOKcO-kZ5` has been set as `GDRIVE_ID`.
The email `anitasingh191975@gmail.com` has been added as `DRIVE_CATEGORY_SA`.

That email alone cannot create Google Drive access. You still need one of these:

- `GDRIVE_ID`: the Railway template uses your folder ID, `1t4m29Fd78WTgLFIh_PXoUTjjOKcO-kZ5`.
- `token.pickle`: generate it with `gen_scripts/gen_token_pickle`, then upload it through bot settings after deploy.
- Service accounts: create `accounts.zip` and upload it through bot settings if you use service accounts.

For a normal personal Drive setup:

1. The provided folder ID is already configured as `GDRIVE_ID`.
2. If you change folders later, copy the new ID from the URL after `/folders/`.
3. Set Railway variable `GDRIVE_ID` to that copied ID.
4. Keep `USE_SERVICE_ACCOUNTS=false`.
5. Deploy the bot.
6. In Telegram, use `/bsetting` or `/usetting` to upload `token.pickle`.

## Railway Steps

1. Create a new Railway project.
2. Deploy from this repository.
3. Railway will use `Dockerfile` and `railway.toml`.
4. Add the variables from `railway.env.example`.
5. Deploy.

`PORT` is provided by Railway automatically. The bot web UI binds to `$PORT`.

## Notes

- `RUN_UPDATE_ON_START=false` is recommended on Railway to avoid mutating the deployed image at runtime.
- `config.py`, `config.env`, tokens, downloads, logs, and local qBittorrent state are excluded from the Docker image by `.dockerignore`.
- If you want torrent/NZB/JDownloader features enabled on Railway, review Railway plan CPU/RAM limits first.
