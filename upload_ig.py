import requests
import time
import os
import sys

# Use environment variables (GitHub Secrets or local .env)
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IG_USER_ID   = os.getenv("INSTAGRAM_USER_ID")

def upload_reel(video_url, caption=""):
    """
    Uploads a video from a public URL to Instagram Reels.
    Flow: 
    1. Create Media Container (POST /{ig-user-id}/media)
    2. Wait for completion (GET /{container-id})
    3. Publish Container (POST /{ig-user-id}/media_publish)
    """
    
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
            print(
                "[!] OAuth token rejected (code 190). "
                "Generate a new long-lived User token in Meta Developer tools, "
                "ensure instagram_basic / instagram_content_publish scopes, "
                "and update the INSTAGRAM_ACCESS_TOKEN GitHub secret (no quotes or newlines).",
                file=sys.stderr,
            )
        return None
        
    container_id = res['id']
    print(f"[+] Container created: {container_id}")
    
    # 2. Check Status (Videos need time to be processed by Meta)
    print("[*] Waiting for video processing...")
    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
    params = {
        'fields': 'status_code',
        'access_token': ACCESS_TOKEN
    }
    
    for i in range(30): # Wait up to 5 minutes
        time.sleep(10)
        sr = requests.get(status_url, params=params)
        sres = sr.json()
        status = sres.get('status_code')
        
        if status == 'FINISHED':
            print("[+] Processing finished.")
            break
        elif status == 'ERROR':
            print(f"[!] Processing failed: {sres}")
            return None
        else:
            print(f"    - Current status: {status} (attempt {i+1}/30)")
    
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
        err = pres.get("error") or {}
        if err.get("code") == 190:
            print(
                "[!] OAuth token rejected at publish (code 190). Refresh INSTAGRAM_ACCESS_TOKEN.",
                file=sys.stderr,
            )
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 upload_ig.py <PUBLIC_VIDEO_URL> [CAPTION]")
    else:
        v_url = sys.argv[1]
        cap = sys.argv[2] if len(sys.argv) > 2 else "New Reel #motivation #quotes"
        upload_reel(v_url, cap)
