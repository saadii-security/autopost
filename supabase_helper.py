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
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    file_name = os.path.basename(local_path)
    
    with open(local_path, 'rb') as f:
        print(f"[*] Uploading {file_name} to Supabase Storage...")
        # Uploading with upsert=True so we can replace if needed
        res = supabase.storage.from_(BUCKET_NAME).upload(
            path=file_name,
            file=f,
            file_options={"x-upsert": "true", "content-type": "video/mp4"}
        )
    
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
