#!/usr/bin/env python3
"""
Run once on your machine to get a refresh token for automated YouTube uploads.

  pip install google-api-python-client google-auth-oauthlib
  python3 setup_youtube_auth.py

Add the printed refresh token to:
  - Local: export YOUTUBE_REFRESH_TOKEN='...'
  - GitHub: repo Settings → Secrets → YOUTUBE_REFRESH_TOKEN

For CI, also add secret GOOGLE_CLIENT_SECRET_JSON with the full contents of
your client_secret*.json file (the file should stay out of git).
"""

import json
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
    print("[*] A browser window will open. Sign in with the Google account for your YouTube channel.")
    print("[*] Enable YouTube Data API v3 in Google Cloud Console for this project if prompted.\n")

    flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print(
            "[!] No refresh token returned. Revoke app access at "
            "https://myaccount.google.com/permissions and run this script again.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Add this to GitHub Actions secrets as YOUTUBE_REFRESH_TOKEN:")
    print("=" * 60)
    print(creds.refresh_token)
    print("=" * 60)
    print("\nOptional: add GOOGLE_CLIENT_SECRET_JSON with this one-line JSON for CI:")
    with open(path, encoding="utf-8") as f:
        print(json.dumps(json.load(f)))
    print("\nLocal test:")
    print(f"  export YOUTUBE_REFRESH_TOKEN='{creds.refresh_token}'")
    print("  python3 upload_youtube.py output_reels/your_reel.mp4")


if __name__ == "__main__":
    main()
