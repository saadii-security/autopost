import os
import sys
from supabase_helper import upload_to_supabase, delete_from_supabase
from upload_ig import upload_reel
from autoreel import get_random_caption

# Update config with env vars
import upload_ig
upload_ig.ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
upload_ig.IG_USER_ID = os.getenv('INSTAGRAM_USER_ID')

local_file = os.getenv('LOCAL_REEL')
caption = get_random_caption('captions.txt')

print(f"[*] Using caption:\n{caption}")

print(f"[*] Uploading to Supabase...")
public_url = upload_to_supabase(local_file)

if public_url:
    print(f"[*] Uploading to Instagram...")
    success = upload_reel(public_url, caption)
    
    # ALWAYS delete from Supabase after Instagram download attempt
    print(f"[*] Cleaning up Supabase...")
    delete_from_supabase(os.path.basename(local_file))
    
    # Delete local file on GitHub runner
    if os.path.exists(local_file):
        os.remove(local_file)
        print(f"[+] Local file deleted.")
else:
    print("[!] Failed to get public URL from Supabase")
    sys.exit(1)
