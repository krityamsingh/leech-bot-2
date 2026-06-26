# PHP / MadelineProto Bridge

Optional microservice that handles Telegram uploads + downloads via PHP's
`danog/madelineproto` library, running side-by-side with the Python (Kurigram)
bot in the **same Railway container**.

## When to enable

You should only enable this if you've already done these and are still hitting
a hard ~1 MB/s ceiling per session:

- `HELPER_STRINGS` filled with at least 2 extra user-sessions
- `HYPER_PIPELINE = 64`, `HYPER_CHUNK = 1MB`, `HYPER_THREADS = 64`
- Verified `tgcrypto` native lib is loaded (check startup log)

If `/speedtest3` shows your single user-session topping out at ~1 MB/s and the
account is non-Premium, **PHP will not help** — the ceiling is Telegram's
per-account throttle, not the library. PHP is the right answer only if
benchmarks show MadelineProto's default parallelism (20 parts) actually beats
Kurigram's at-100 setting in your environment.

## One-time setup (Railway)

1. **Add a Persistent Volume** (Railway → Service → Volumes → Add):
   - Mount path: `/usr/src/app/php-bridge/data`
   - Size: 1 GB is plenty (session file is ~100 KB)
   - Without this, the session is **wiped on every redeploy** and you'll
     have to re-login each time. This costs ~₹50/month on Railway.

2. **Flip the flag** in `config.py`:
   ```python
   USE_PHP_TRANSPORT = True
   ```

3. **Push + Redeploy** so the image installs PHP 8.2 + composer + MadelineProto.
   First deploy takes ~3-4 extra minutes (PHP packages + `composer install`).

4. **Login once** via Railway shell:
   ```bash
   railway shell  # or use the Railway dashboard Run command
   cd /usr/src/app/php-bridge
   php login.php
   ```
   Follow the prompts (phone number → OTP → optional 2FA password). Use the
   **same Telegram account** that's already in `USER_SESSION_STRING` — there's
   no benefit to using a different account here.

5. **Restart the service** (Railway → Restart). On startup, `start.sh` will
   detect `session.madeline` and launch `server.php` on `127.0.0.1:9090`.

## How the failover works

```
Upload flow:
  TelegramUploader._upload_file()
    │
    ├─ if USE_PHP_TRANSPORT → POST /upload to php-bridge
    │     ├─ success → fetch Message via Kurigram, return
    │     └─ failure → fall through to HyperUP (no break)
    │
    └─ else → existing Kurigram HyperUP path

Download flow:
  TelegramDownloadHelper._download()
    │
    ├─ if USE_PHP_TRANSPORT → POST /download to php-bridge
    │     ├─ success → file at save_path, return
    │     └─ failure → fall through to HyperDL → standard
    │
    ├─ else if USE_HYPER → HyperDL
    └─ else → standard
```

The Python client (`bot/helper/ext_utils/php_bridge.py`) has a 3-strike circuit
breaker: after 3 consecutive failures it goes OPEN for 60 seconds and returns
None immediately, so a temporarily-stuck PHP service can never break a leech.

## Disabling

Two options:

- **Temporarily**: set `USE_PHP_TRANSPORT = False` in config.py and redeploy.
  The bridge process won't start; Kurigram path is used for everything.
- **Permanently** (smaller container): delete `php-bridge/` directory and
  revert the `apt-get install php8.2-*` block in `Dockerfile`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `[php-bridge] ERROR: session.madeline not found` | Login never ran, or volume not mounted | Run `php login.php` in Railway shell |
| `php_bridge: 3 consecutive failures` in Python log | PHP daemon crashed or unreachable | Check Railway logs for `[php-bridge]` lines; restart service |
| Upload starts via PHP but goes to wrong chat | `peer` int cast didn't match expected channel ID format | Channel IDs need `-100` prefix; check `LEECH_DUMP_CHAT` |
| Still ~1 MB/s after enabling | Account-side throttle (non-Premium) | PHP can't fix this; add HELPER_STRINGS or get Premium |
| Re-OTP required after every redeploy | Volume not mounted | Add Persistent Volume at `/usr/src/app/php-bridge/data` |

## Files

```
php-bridge/
├── composer.json         # requires danog/madelineproto ^8.4 + amphp/http-server
├── login.php             # interactive first-time session creation
├── server.php            # the daemon: AMPHP HTTP server on 127.0.0.1:9090
└── data/                 # session.madeline (gitignored; needs Railway Volume)

bot/helper/ext_utils/
└── php_bridge.py         # thin httpx async client + circuit breaker

bot/helper/mirror_leech_utils/
├── upload_utils/telegram_uploader.py      # _try_php_upload hook
└── download_utils/telegram_download.py    # _php_download hook
```
