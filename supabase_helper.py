import os
import sys
from supabase import create_client, Client

# Use environment variables (GitHub Secrets or local .env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME  = "reels"

def upload_to_supabase(local_path):
    """
    Uploads a file to Supabase Storage and returns a public URL.
    """
    _debug = os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("AUTOREEL_DEBUG", "")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(
            "[!] SUPABASE_URL or SUPABASE_KEY missing from environment",
            file=sys.stderr,
        )
        if _debug:
            print(
                f"[debug supabase] SUPABASE_URL set={bool(SUPABASE_URL)} SUPABASE_KEY set={bool(SUPABASE_KEY)}",
                file=sys.stderr,
            )
        return None

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    file_name = os.path.basename(local_path)
    
    try:
        with open(local_path, 'rb') as f:
            print(f"[*] Uploading {file_name} to Supabase Storage...")
            # Uploading with upsert=True so we can replace if needed
            res = supabase.storage.from_(BUCKET_NAME).upload(
                path=file_name,
                file=f,
                file_options={"x-upsert": "true", "content-type": "video/mp4"}
            )
            if _debug:
                print(f"[debug supabase] upload response: {res}", file=sys.stderr)
    except Exception as e:
        print(f"[!] Supabase upload failed: {e}", file=sys.stderr)
        if _debug:
            import traceback
            traceback.print_exc()
        return None
    
    # Generate Public URL
    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
    print(f"[+] File available at: {public_url}")
    return public_url

def delete_from_supabase(file_name):
    """
    Cleanup after Instagram has downloaded the file.
    """
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.storage.from_(BUCKET_NAME).remove([file_name])
    print(f"[-] Deleted {file_name} from Supabase.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 supabase_helper.py <LOCAL_FILE_PATH>")
    else:
        url = upload_to_supabase(sys.argv[1])
        print(f"PUBLIC_URL={url}")
