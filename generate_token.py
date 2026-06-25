#!/usr/bin/env python3
"""
One-click Google Drive token.pickle generator.
Run this script from the leach-bot root directory:
    python3 generate_token.py
"""

import os
import sys
import pickle
import socket
import webbrowser

# ── Check dependencies ─────────────────────────────────────────────────────────
try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("\n[!] Missing Google libraries. Installing now...")
    os.system(f"{sys.executable} -m pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client -q")
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "gen_scripts", "config", "credentials.json")
TOKEN_FILE       = os.path.join(SCRIPT_DIR, "token.pickle")

# ── Scopes ─────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0

def find_free_port(start=8085, end=8095):
    for p in range(start, end):
        if port_free(p):
            return p
    return None

def main():
    print("\n" + "=" * 55)
    print("   Google Drive token.pickle Generator")
    print("=" * 55)

    # ── Check credentials file ─────────────────────────────────────────────────
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n[ERROR] credentials.json not found at:\n  {CREDENTIALS_FILE}")
        sys.exit(1)
    print(f"\n[OK] Found credentials.json")

    # ── Check for existing valid token ─────────────────────────────────────────
    creds = None
    if os.path.exists(TOKEN_FILE):
        print(f"[INFO] Existing token.pickle found — checking validity...")
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
        if creds and creds.valid:
            print("[OK] Token is still valid! Nothing to do.")
            print(f"\n>>> Token location: {TOKEN_FILE}")
            return
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] Token expired. Refreshing...")
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "wb") as f:
                    pickle.dump(creds, f)
                print(f"[OK] Token refreshed and saved to:\n  {TOKEN_FILE}")
                return
            except Exception as e:
                print(f"[WARN] Refresh failed ({e}), generating new token...")
                creds = None

    # ── Generate new token ─────────────────────────────────────────────────────
    print("\n[INFO] Starting Google OAuth flow...")
    print("[INFO] A browser window will open — log in with your Google account")
    print("       and allow ALL requested permissions.\n")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    port = find_free_port()
    if port:
        print(f"[INFO] Using local port {port} for OAuth callback...")
        try:
            creds = flow.run_local_server(port=port, open_browser=True, prompt="consent")
        except Exception as e:
            print(f"[WARN] Local server failed: {e}\nFalling back to console auth...")
            creds = flow.run_console()
    else:
        print("[INFO] No free port found. Using console auth...")
        creds = flow.run_console()

    # ── Save token ─────────────────────────────────────────────────────────────
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)

    print("\n" + "=" * 55)
    print("   SUCCESS! token.pickle generated.")
    print("=" * 55)
    print(f"\n>>> Saved to: {TOKEN_FILE}")
    print("\n>>> Now restart the bot:")
    print("    python3 -m bot")
    print("\nYou're all set! Use /mirror in Telegram to upload to GDrive.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Cancelled by user]")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
