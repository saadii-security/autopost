"""
Upload a generated reel to YouTube (Shorts-friendly vertical video).

Auth:
  - GOOGLE_CLIENT_SECRET_JSON: full client secret JSON (GitHub Actions)
  - GOOGLE_CLIENT_SECRET_FILE or client_secret*.json locally
  - YOUTUBE_REFRESH_TOKEN: refresh token from setup_youtube_auth.py
"""

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_CATEGORY = "22"  # People & Blogs


def _debug(msg: str) -> None:
    if os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("AUTOREEL_DEBUG"):
        print(f"[debug youtube] {msg}", file=sys.stderr)


def _load_client_config():
    raw = os.getenv("GOOGLE_CLIENT_SECRET_JSON", "").strip()
    if raw:
        return json.loads(raw)

    path = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "").strip()
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    for candidate in sorted(Path(".").glob("client_secret*.json")):
        with open(candidate, encoding="utf-8") as f:
            return json.load(f)

    return None


def _client_id_secret(config):
    block = config.get("installed") or config.get("web") or {}
    client_id = block.get("client_id")
    client_secret = block.get("client_secret")
    if not client_id or not client_secret:
        raise ValueError("client secret JSON missing client_id or client_secret")
    return client_id, client_secret


def is_youtube_configured():
    refresh = (os.getenv("YOUTUBE_REFRESH_TOKEN") or "").strip()
    if not refresh:
        return False
    try:
        _client_id_secret(_load_client_config() or {})
        return True
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def get_youtube_credentials():
    refresh_token = (os.getenv("YOUTUBE_REFRESH_TOKEN") or "").strip()
    if not refresh_token:
        raise RuntimeError("YOUTUBE_REFRESH_TOKEN is not set")

    config = _load_client_config()
    if not config:
        raise RuntimeError(
            "No Google client secret found. Set GOOGLE_CLIENT_SECRET_JSON, "
            "GOOGLE_CLIENT_SECRET_FILE, or add client_secret*.json in the project root."
        )

    client_id, client_secret = _client_id_secret(config)
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def list_my_channels():
    """Print channels this token can upload to (for verifying the right account)."""
    yt = build("youtube", "v3", credentials=get_youtube_credentials(), cache_discovery=False)
    res = yt.channels().list(part="snippet", mine=True).execute()
    return [
        (item["snippet"]["title"], item["id"])
        for item in res.get("items", [])
    ]


def build_title_description(caption, used_quote=None):
    if used_quote:
        base = used_quote.replace("\n", " ").strip()
    else:
        base = caption.split("\n")[0].strip() if caption else "Motivation"

    title = base[:100]
    if len(base) > 100:
        title = base[:97] + "..."

    description = caption or base
    if "#shorts" not in description.lower() and "#shorts" not in title.lower():
        description = f"{description.rstrip()}\n\n#Shorts"

    tags = []
    for word in description.split():
        if word.startswith("#") and len(word) > 1:
            tags.append(word[1:][:30])
    tags = tags[:15]

    return title, description, tags


def upload_short(
    local_path,
    caption="",
    used_quote=None,
    *,
    privacy_status=None,
    category_id=None,
):
    if not os.path.isfile(local_path):
        print(f"[!] Video file not found: {local_path}", file=sys.stderr)
        return None

    privacy = (privacy_status or os.getenv("YOUTUBE_PRIVACY", "public")).strip()
    category = (category_id or os.getenv("YOUTUBE_CATEGORY_ID", DEFAULT_CATEGORY)).strip()

    try:
        creds = get_youtube_credentials()
    except Exception as e:
        print(f"[!] YouTube auth failed: {e}", file=sys.stderr)
        return None

    title, description, tags = build_title_description(caption, used_quote)
    _debug(f"title={title!r} privacy={privacy!r}")

    try:
        channels = list_my_channels()
        if channels:
            print(f"[*] Uploading as YouTube channel: {channels[0][0]}")
    except Exception:
        pass

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        local_path,
        mimetype="video/mp4",
        chunksize=1024 * 1024,
        resumable=True,
    )

    print(f"[*] Uploading to YouTube: {os.path.basename(local_path)}")
    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"    ... upload {pct}%")

        video_id = response.get("id")
        print(f"[SUCCESS] YouTube video published: https://www.youtube.com/watch?v={video_id}")
        return video_id
    except HttpError as e:
        print(f"[!] YouTube API error: {e}", file=sys.stderr)
        if e.content:
            print(f"[!] Response: {e.content.decode(errors='replace')[:500]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[!] YouTube upload failed: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 upload_youtube.py <LOCAL_VIDEO.mp4> [CAPTION]")
        sys.exit(1)
    path = sys.argv[1]
    cap = sys.argv[2] if len(sys.argv) > 2 else ""
    vid = upload_short(path, cap)
    sys.exit(0 if vid else 1)
