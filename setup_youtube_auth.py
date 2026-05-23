#!/usr/bin/env python3
"""
One-time OAuth for the YouTube channel that should receive Shorts.

Before running:
  1. Open youtube.com and switch to your NEW reels channel.
  2. Add your Google email under OAuth consent screen → Test users (if app is in Testing).

  pip install -r requirements.txt
  python3 setup_youtube_auth.py

Add YOUTUBE_REFRESH_TOKEN to GitHub Secrets.
Add GOOGLE_CLIENT_SECRET_JSON from your local client_secret*.json (do not commit that file).
"""

import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _find_client_secret():
    for p in sorted(Path(".").glob("client_secret*.json")):
        return str(p)
    return None


def main():
    path = _find_client_secret()
    if not path:
        print("[!] Put client_secret*.json in this directory.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Using client secrets: {path}")
    print("[*] IMPORTANT: In your browser, switch to the YouTube channel for reels FIRST.")
    print("[*] Then sign in with that channel's Google account when prompted.\n")

    flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print(
            "[!] No refresh token. Revoke app at https://myaccount.google.com/permissions "
            "and run again.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\n" + "=" * 60)
    print("GitHub secret: YOUTUBE_REFRESH_TOKEN")
    print("=" * 60)
    print(creds.refresh_token)
    print("=" * 60)
    print("\nGitHub secret: GOOGLE_CLIENT_SECRET_JSON")
    print("  → paste the full contents of", path)
    print("  → never commit that file (it is in .gitignore)")
    print("\nVerify channel:")
    print("  export YOUTUBE_REFRESH_TOKEN='<token above>'")
    print("  python3 -c \"from upload_youtube import list_my_channels; print(list_my_channels())\"")


if __name__ == "__main__":
    main()
