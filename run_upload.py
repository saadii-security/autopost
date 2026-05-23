import os
import sys
import subprocess
from supabase_helper import upload_to_supabase, delete_from_supabase
from upload_ig import upload_reel
from upload_youtube import upload_short, is_youtube_configured
from autoreel import get_random_caption, _remove_quote_from_file

# Update config with env vars
import upload_ig
upload_ig.ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
upload_ig.IG_USER_ID = os.getenv('INSTAGRAM_USER_ID')

_DEBUG = os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("AUTOREEL_DEBUG", "")


def _dbg(msg: str) -> None:
    if _DEBUG:
        print(f"[debug run_upload] {msg}", file=sys.stderr)


local_file = os.getenv('LOCAL_REEL')
_dbg(f"LOCAL_REEL={local_file!r} exists={bool(local_file and os.path.isfile(local_file))}")
_dbg(
    "secrets present: "
    f"SUPABASE_URL={'yes' if os.getenv('SUPABASE_URL') else 'no'}, "
    f"SUPABASE_KEY={'yes' if os.getenv('SUPABASE_KEY') else 'no'}, "
    f"INSTAGRAM_ACCESS_TOKEN={'yes' if os.getenv('INSTAGRAM_ACCESS_TOKEN') else 'no'}, "
    f"INSTAGRAM_USER_ID={'yes' if os.getenv('INSTAGRAM_USER_ID') else 'no'}, "
    f"YOUTUBE_REFRESH_TOKEN={'yes' if os.getenv('YOUTUBE_REFRESH_TOKEN') else 'no'}, "
    f"GOOGLE_CLIENT_SECRET_JSON={'yes' if os.getenv('GOOGLE_CLIENT_SECRET_JSON') else 'no'}, "
    f"youtube_configured={is_youtube_configured()}"
)

caption = get_random_caption('captions.txt')

print(f"[*] Using caption:\n{caption}")

if not local_file:
    print("[!] LOCAL_REEL is not set or empty", file=sys.stderr)
    sys.exit(1)

if not os.path.isfile(local_file):
    print(f"[!] LOCAL_REEL file not found: {local_file}", file=sys.stderr)
    sys.exit(1)

# Read the used quote from the file saved by autoreel.py
used_quote = None
if os.path.exists(".used_quote.txt"):
    with open(".used_quote.txt", "r", encoding="utf-8") as f:
        used_quote = f.read().strip()
    _dbg(f"Used quote: {used_quote[:50]!r}...")
else:
    _dbg("No .used_quote.txt found")

youtube_configured = is_youtube_configured()
youtube_success = True

if youtube_configured:
    print("[*] Uploading to YouTube...")
    youtube_success = bool(upload_short(local_file, caption, used_quote))
elif os.environ.get("GITHUB_ACTIONS") == "true":
    print(
        "[!] YouTube not configured (need YOUTUBE_REFRESH_TOKEN + GOOGLE_CLIENT_SECRET_JSON). "
        "Skipping YouTube; Instagram-only run.",
        file=sys.stderr,
    )

print(f"[*] Uploading to Supabase...")
public_url = upload_to_supabase(local_file)

if public_url:
    print(f"[*] Uploading to Instagram...")
    ig_success = upload_reel(public_url, caption)

    # ALWAYS delete from Supabase after Instagram download attempt
    print(f"[*] Cleaning up Supabase...")
    delete_from_supabase(os.path.basename(local_file))

    # Delete local file on GitHub runner
    if os.path.exists(local_file):
        os.remove(local_file)
        print(f"[+] Local file deleted.")

    # Remove used quote from qoutes.txt and commit to git
    publish_ok = ig_success and youtube_success
    if used_quote and publish_ok:
        print(f"[*] Removing used quote from qoutes.txt...")
        if _remove_quote_from_file(used_quote, "qoutes.txt"):
            # Commit and push the change to git
            print(f"[*] Committing quote removal to git...")
            try:
                subprocess.run(["git", "config", "user.name", "github-actions"], check=True, capture_output=True)
                subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True, capture_output=True)
                subprocess.run(["git", "add", "qoutes.txt"], check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Remove used quote from qoutes.txt"], check=True, capture_output=True)
                # Push using the PAT from environment
                pat = os.getenv("GIT_PAT")
                if pat:
                    repo_url = f"https://{pat}@github.com/saadii-security/autopost.git"
                    subprocess.run(["git", "push", repo_url, "main"], check=True, capture_output=True)
                    print(f"[+] Quote removal committed and pushed to git.")
                else:
                    print(f"[!] GIT_PAT not set, skipping push.", file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print(f"[!] Git operation failed: {e}", file=sys.stderr)

    if not ig_success:
        print(
            "[!] Instagram Reel was not published. Check run logs above and your token.",
            file=sys.stderr,
        )
        sys.exit(1)
    if youtube_configured and not youtube_success:
        print(
            "[!] YouTube upload failed. Check run logs and OAuth / API setup.",
            file=sys.stderr,
        )
        sys.exit(1)
else:
    print("[!] Failed to get public URL from Supabase")
    sys.exit(1)
