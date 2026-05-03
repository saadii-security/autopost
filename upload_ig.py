import requests
import time
import os
import sys

ACCESS_TOKEN = (os.getenv("INSTAGRAM_ACCESS_TOKEN") or "").strip().strip('"').strip("'")
IG_USER_ID   = (os.getenv("INSTAGRAM_USER_ID") or "").strip()

# Debug — prints first/last 6 chars so you can verify in logs
print(f"[*] Token preview: {ACCESS_TOKEN[:6]}...{ACCESS_TOKEN[-6:]}")
print(f"[*] Token length: {len(ACCESS_TOKEN)}")
print(f"[*] User ID: {IG_USER_ID}")

def upload_reel(video_url, caption=""):
    
    # 1. Create Container
    print(f"[*] Creating media container for {video_url[:50]}...")
    url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
        'access_token': ACCESS_TOKEN
    }
    
    r = requests.post(url, data=payload)
    res = r.json()
    
    if 'id' not in res:
        print(f"[!] Error creating container: {res}")
        err = res.get("error") or {}
        if err.get("code") == 190:
            print("[!] OAuth token rejected (code 190).", file=sys.stderr)
            print(f"[!] Token length was: {len(ACCESS_TOKEN)}", file=sys.stderr)
            print(f"[!] Token starts with: {ACCESS_TOKEN[:10]}", file=sys.stderr)
        return None
        
    container_id = res['id']
    print(f"[+] Container created: {container_id}")
    
    # 2. Check Status
    print("[*] Waiting for video processing...")
    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
    params = {
        'fields': 'status_code',
        'access_token': ACCESS_TOKEN
    }
    
    for i in range(30):
        time.sleep(10)
        sr = requests.get(status_url, params=params)
        sres = sr.json()
        status = sres.get('status_code')
        
        if status == 'FINISHED':
            print("[SUCCESS] Video is ready for publishing.")
            break
        elif status == 'ERROR':
            # NEW: Get detailed error message
            error_details_url = f"https://graph.facebook.com/v19.0/{container_id}"
            err_params = {'fields': 'status_code,status,error_message', 'access_token': ACCESS_TOKEN}
            err_r = requests.get(error_details_url, params=err_params)
            print(f"[!] Processing failed: {sres}")
            print(f"[!] Detailed Instagram Error: {err_r.json()}")
            return None
        else:
            print(f"    ... current status: {status} (attempt {i+1}/30)")
    
    # 3. Publish
    print("[*] Publishing reel...")
    publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    publish_payload = {
        'creation_id': container_id,
        'access_token': ACCESS_TOKEN
    }
    
    pr = requests.post(publish_url, data=publish_payload)
    pres = pr.json()
    
    if 'id' in pres:
        print(f"[SUCCESS] Reel published! ID: {pres['id']}")
        return pres['id']
    else:
        print(f"[!] Publish failed: {pres}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 upload_ig.py <PUBLIC_VIDEO_URL> [CAPTION]")
    else:
        v_url = sys.argv[1]
        cap = sys.argv[2] if len(sys.argv) > 2 else "New Reel #motivation #quotes"
        upload_reel(v_url, cap)