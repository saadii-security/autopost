"""
Quote Reel Video Generator
Inspired by aesthetic quote pages like sunxy.17

Style:
  - 9:16 vertical (1080x1920) - Instagram Reels spec
  - Dark/cinematic grain background with radial vignette
  - Centered serif italic quote + thin author line
  - Smooth fade-in / fade-out
  - Slow Ken-Burns zoom over duration

Usage:
    python3 quote_reel_generator.py
        -> random demo reel

    python3 quote_reel_generator.py --quote "Your text\nLine 2" --author "Name" --theme dark
        -> single custom reel

    python3 quote_reel_generator.py --batch
        -> all quotes in QUOTES list

    python3 quote_reel_generator.py --add-audio lofi.mp3
        -> merge bgm audio track

Requirements:
    pip install pillow numpy
    ffmpeg installed (apt install ffmpeg)
"""

import os, sys, random, shutil, argparse, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ───────────────────────────────────────────────────────
#  QUOTE BANK  (sunxy.17 style)
# ───────────────────────────────────────────────────────
QUOTES = [
    {
        "text": "She had a galaxy in her eyes\nand he never learned\nhow to stargaze.",
        "author": "r.h. Sin",
        "theme": "dark",
    },
    {
        "text": "Be selective with your energy.\nNot everyone deserves\nfront row seats to your life.",
        "author": "unknown",
        "theme": "dark",
    },
    {
        "text": "She was not made\nto be understood.\nShe was made to be loved.",
        "author": "F. Scott Fitzgerald",
        "theme": "moody",
    },
    {
        "text": "Some people are not\nmeant to stay forever.\nThey are lessons.",
        "author": "unknown",
        "theme": "dark",
    },
    {
        "text": "Healing is not linear.\nSome days you bloom.\nSome days you just breathe.",
        "author": "unknown",
        "theme": "warm",
    },
    {
        "text": "Stop explaining yourself\nto people who are committed\nto misunderstanding you.",
        "author": "unknown",
        "theme": "dark",
    },
    {
        "text": "You were the poem\nI never knew how\nto write.",
        "author": "unknown",
        "theme": "moody",
    },
    {
        "text": "Protect your peace\nlike it is the most\nprecious thing you own.",
        "author": "unknown",
        "theme": "warm",
    },
    {
        "text": "She wasn't heartless.\nShe just learned\nhow to use her heart less.",
        "author": "r.h. Sin",
        "theme": "dark",
    },
    {
        "text": "Not everyone who smiles\nat you is your friend.\nLearn the difference.",
        "author": "unknown",
        "theme": "dark",
    },
    {
        "text": "Growth is painful.\nChange is painful.\nBut nothing is as painful\nas staying stuck.",
        "author": "unknown",
        "theme": "warm",
    },
    {
        "text": "Be the energy\nyou want\nto attract.",
        "author": "unknown",
        "theme": "moody",
    },
]


def _load_quotes_file(path):
    if not path:
        return []
    if not os.path.exists(path):
        print(f"Warning: quotes file not found: {path}", file=sys.stderr)
        return []

    items = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line[0].isdigit():
                parts = line.split(".", 1)
                if len(parts) == 2 and parts[0].strip().isdigit():
                    line = parts[1].strip()
            if line:
                items.append(line)
    return items


def _load_captions(path="captions.txt"):
    if not os.path.exists(path):
        return [], ""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    hashtags = ""
    quote_captions = []
    
    for b in blocks:
        if b.startswith("#"):
            hashtags = b
        else:
            line = b
            if line and line[0].isdigit():
                parts = line.split(".", 1)
                if len(parts) == 2 and parts[0].strip().isdigit():
                    line = parts[1].strip()
            quote_captions.append(line)
    return quote_captions, hashtags


def get_random_caption(path="captions.txt"):
    captions, hashtags = _load_captions(path)
    if not captions:
        return hashtags
    return f"{random.choice(captions)}\n\n{hashtags}"


# ───────────────────────────────────────────────────────
#  THEME PALETTES
# ───────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":       (8,   8,  12),
        "vignette": 0.75,
        "text":     (240, 235, 228),
        "author":   (160, 150, 140),
        "line":     ( 90,  80,  70),
        "grain":    0.045,
    },
    "moody": {
        "bg":       (12,  10,  18),
        "vignette": 0.70,
        "text":     (235, 230, 240),
        "author":   (140, 130, 160),
        "line":     ( 80,  70, 110),
        "grain":    0.040,
    },
    "warm": {
        "bg":       (16,  12,   8),
        "vignette": 0.65,
        "text":     (245, 238, 225),
        "author":   (180, 160, 130),
        "line":     (110,  90,  60),
        "grain":    0.035,
    },
}

# ───────────────────────────────────────────────────────
#  VIDEO SETTINGS
# ───────────────────────────────────────────────────────
WIDTH          = 1080
HEIGHT         = 1920
FPS            = 30
DURATION       = 8       # seconds
FADE_IN        = 0.8
FADE_OUT       = 0.8
TOTAL_FRAMES   = DURATION * FPS
LINE_SPACING   = 92
MAX_TEXT_WIDTH = int(WIDTH * 0.78)

FONT_QUOTE  = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_AUTHOR = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Helvetica Neue.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_Q_FB   = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
FONT_A_FB   = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
SIZE_QUOTE  = 45
SIZE_AUTHOR = 34

MAX_QUOTE_LINES = 3
LEFT_PAD_PX = int(WIDTH * 0.10)
STRIP_X0_PX = int(WIDTH * 0.06)
STRIP_X1_PX = int(WIDTH * 0.075)
STRIP_COLOR = (210, 24, 36)


def _load_font(path, fallback, size):
    candidates = []
    if isinstance(path, (list, tuple)):
        candidates.extend(path)
    else:
        candidates.append(path)
    if isinstance(fallback, (list, tuple)):
        candidates.extend(fallback)
    else:
        candidates.append(fallback)

    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass

    f = ImageFont.load_default()
    print("Warning: Could not load TTF fonts; using PIL default font (output may look tiny).", file=sys.stderr)
    return f


def _vignette(w, h, strength):
    cx, cy = w / 2.0, h / 2.0
    Y, X = np.ogrid[:h, :w]
    d = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    v = np.clip(1.0 - d * strength, 0.0, 1.0).astype(np.float32)
    return np.stack([v, v, v], axis=-1)


def _wrap_text(text, font, max_w, draw):
    lines = []
    for para in text.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = ""
        for word in words:
            test = (cur + " " + word).strip()
            bb = draw.textbbox((0, 0), test, font=font)
            if (bb[2] - bb[0]) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def _line_height(draw, font):
    bb = draw.textbbox((0, 0), "Ag", font=font)
    return max(1, bb[3] - bb[1])


def _fit_quote_to_lines(quote_text, draw, *, max_lines=MAX_QUOTE_LINES, max_w=MAX_TEXT_WIDTH, start_size=SIZE_QUOTE, min_size=26):
    size = start_size
    while size >= min_size:
        f = _load_font(FONT_QUOTE, FONT_Q_FB, size)
        lines = _wrap_text(quote_text, f, max_w, draw)
        if len(lines) <= max_lines:
            lh = _line_height(draw, f)
            gap = int(round(lh * 0.30))
            return f, lines, lh, gap
        size -= 2

    f = _load_font(FONT_QUOTE, FONT_Q_FB, min_size)
    lines = _wrap_text(quote_text, f, max_w, draw)[:max_lines]
    lh = _line_height(draw, f)
    gap = int(round(lh * 0.30))
    return f, lines, lh, gap


def render_frame(idx, quote_text, author, cfg, font_q, font_a, vig, *, lines, line_h, line_gap, block_x):
    t    = idx / FPS
    prog = idx / max(TOTAL_FRAMES - 1, 1)

    # Background
    base = np.full((HEIGHT, WIDTH, 3), cfg["bg"], dtype=np.float32)
    grad = np.linspace(0, 18, HEIGHT, dtype=np.float32).reshape(-1, 1, 1)
    base += grad * 0.25
    base *= vig

    # Film grain (seeded for determinism)
    rng  = np.random.default_rng(idx * 7 + 13)
    base += rng.normal(0, cfg["grain"] * 255, base.shape)
    base  = np.clip(base, 0, 255).astype(np.uint8)
    img   = Image.fromarray(base)

    # Ken-Burns zoom
    zoom = 1.00 + 0.04 * prog
    zw, zh = int(WIDTH * zoom), int(HEIGHT * zoom)
    px, py = (zw - WIDTH) // 2, (zh - HEIGHT) // 2
    img = img.resize((zw, zh), Image.LANCZOS)
    img = img.crop((px, py, px + WIDTH, py + HEIGHT))

    # Text
    draw  = ImageDraw.Draw(img)
    total_h = len(lines) * line_h + max(0, len(lines) - 1) * line_gap
    y0 = (HEIGHT - total_h) // 2

    strip_y0 = max(0, y0 - 8)
    strip_y1 = min(HEIGHT, y0 + total_h + int(line_h * 1.25))
    strip_x0 = max(0, block_x - (STRIP_X1_PX - STRIP_X0_PX) - int(WIDTH * 0.02))
    strip_x1 = strip_x0 + (STRIP_X1_PX - STRIP_X0_PX)
    draw.rectangle([strip_x0, strip_y0, strip_x1, strip_y1], fill=STRIP_COLOR)

    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font_q)
        x  = block_x
        y  = y0 + i * (line_h + line_gap)
        draw.text((x + 2, y + 2), line, font=font_q, fill=(0, 0, 0, 90))
        draw.text((x, y),         line, font=font_q, fill=cfg["text"])

    # Author
    auth = f"— {author}"
    bb   = draw.textbbox((0, 0), auth, font=font_a)
    draw.text((block_x, y0 + total_h + int(line_h * 0.85)), auth, font=font_a, fill=cfg["author"])

    # Fade
    alpha = min(t / FADE_IN, 1.0, (DURATION - t) / FADE_OUT)
    alpha = max(0.0, alpha)
    if alpha < 1.0:
        arr = (np.array(img).astype(np.float32) * alpha).astype(np.uint8)
        img = Image.fromarray(arr)

    return img


# ───────────────────────────────────────────────────────
#  VIDEO BUILDER
# ───────────────────────────────────────────────────────

def generate_video(quote_text, author, theme, output_path):
    cfg       = THEMES.get(theme, THEMES["dark"])
    tmp_dir   = f"/tmp/_qr_{os.getpid()}"
    os.makedirs(tmp_dir, exist_ok=True)
    out_dir   = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    scratch = Image.new("RGB", (WIDTH, HEIGHT), cfg["bg"])
    scratch_draw = ImageDraw.Draw(scratch)
    font_q, lines, line_h, line_gap = _fit_quote_to_lines(quote_text, scratch_draw)
    font_a = _load_font(FONT_AUTHOR, FONT_A_FB, SIZE_AUTHOR)
    vig    = _vignette(WIDTH, HEIGHT, cfg["vignette"])

    widths = []
    for line in lines:
        bb = scratch_draw.textbbox((0, 0), line, font=font_q)
        widths.append(bb[2] - bb[0])
    auth = f"— {author}"
    bb = scratch_draw.textbbox((0, 0), auth, font=font_a)
    widths.append(bb[2] - bb[0])
    block_w = max(widths) if widths else int(WIDTH * 0.5)
    block_x = max(0, (WIDTH - block_w) // 2)

    print(f"  Rendering {TOTAL_FRAMES} frames…")
    for i in range(TOTAL_FRAMES):
        frame = render_frame(i, quote_text, author, cfg, font_q, font_a, vig, lines=lines, line_h=line_h, line_gap=line_gap, block_x=block_x)
        frame.save(f"{tmp_dir}/f{i:05d}.png")
        if i % 60 == 0:
            print(f"    {i}/{TOTAL_FRAMES}")

    print("  Encoding…")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{tmp_dir}/f%05d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "fast",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("  ffmpeg error:", r.stderr[-400:])
    else:
        print(f"  -> {output_path}")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return output_path


def merge_audio(video_path, audio_path, output_path, duration=8):
    # Get audio duration to pick a random segment if it's long
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
    try:
        audio_dur = float(subprocess.check_output(probe_cmd).decode().strip())
    except:
        audio_dur = duration

    start_t = 0
    if audio_dur > duration + 5:
        # Pick a random start point, leaving room for the duration
        start_t = random.uniform(0, audio_dur - duration - 2)

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_t:.2f}",
        "-t", str(duration),
        "-i", audio_path,
        "-i", video_path,
        "-map", "0:a", "-map", "1:v",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", f"afade=t=out:st={duration-2}:d=2", # Fade out audio at the end
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("  audio error:", r.stderr[-300:])
    else:
        print(f"  -> {output_path}")


# ───────────────────────────────────────────────────────
#  CLI
# ───────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Quote Reel Generator (sunxy.17 style)")
    p.add_argument("--quote",  type=str)
    p.add_argument("--author", type=str, default="unknown")
    p.add_argument("--theme",  choices=["dark", "moody", "warm"], default="dark")
    p.add_argument("--output", type=str, default="output_reels/reel.mp4")
    p.add_argument("--batch",  action="store_true")
    p.add_argument("--add-audio", type=str, metavar="AUDIO", help="Path to audio file or directory")
    p.add_argument("--quotes-file", type=str, default="qoutes.txt")
    p.add_argument("--author-default", type=str, default="unknown")
    args = p.parse_args()

    os.makedirs("output_reels", exist_ok=True)

    file_quotes = _load_quotes_file(args.quotes_file)
    file_bank = [{"text": t, "author": args.author_default, "theme": args.theme} for t in file_quotes]
    bank = file_bank if file_bank else QUOTES

    audio_file = args.add_audio
    if audio_file and os.path.isdir(audio_file):
        exts = (".mp3", ".wav", ".m4a", ".aac")
        files = [os.path.join(audio_file, f) for f in os.listdir(audio_file) if f.lower().endswith(exts)]
        if files:
            audio_file = random.choice(files)

    if args.batch:
        print(f"\nBatch: {len(bank)} reels\n")
        for idx, q in enumerate(bank, 1):
            slug = q["text"].split("\n")[0][:25].replace(" ", "_").lower()
            # Added timestamp to filename to prevent overwriting previous runs
            import time
            ts = int(time.time())
            out  = f"output_reels/reel_{idx:02d}_{slug}_{ts}.mp4"
            print(f"[{idx}/{len(bank)}] {q['text'][:50].replace(chr(10), ' ')}")
            generate_video(q["text"], q.get("author", "unknown"), q.get("theme", args.theme), out)
            if audio_file:
                current_audio = audio_file
                if args.add_audio and os.path.isdir(args.add_audio):
                    exts = (".mp3", ".wav", ".m4a", ".aac")
                    current_audio = random.choice([os.path.join(args.add_audio, f) for f in os.listdir(args.add_audio) if f.lower().endswith(exts)])
                final_out = out.replace(".mp4", "_audio.mp4")
                merge_audio(out, current_audio, final_out, duration=DURATION)
                # Remove the silent version
                if os.path.exists(out) and os.path.exists(final_out):
                    os.remove(out)
                
                # Check for upload triggers or automate if in autopilot
                # For now, we'll just log it.

        print(f"\nDone. Videos in ./output_reels/")

    elif args.quote:
        text = args.quote.replace("\\n", "\n")
        print(f'Generating: "{text[:60].replace(chr(10)," ")}"')
        out  = args.output
        # If the output path already exists, append a timestamp
        if os.path.exists(out):
            import time
            base, ext = os.path.splitext(out)
            out = f"{base}_{int(time.time())}{ext}"
            
        generate_video(text, args.author, args.theme, out)
        if audio_file:
            final_out = out.replace(".mp4", "_audio.mp4")
            merge_audio(out, audio_file, final_out, duration=DURATION)
            # Remove the silent version
            if os.path.exists(out) and os.path.exists(final_out):
                os.remove(out)

    else:
        q   = random.choice(bank)
        import time
        ts = int(time.time())
        out = f"output_reels/demo_reel_{ts}.mp4"
        print(f'Demo: "{q["text"].replace(chr(10)," ")}"')
        generate_video(q["text"], q.get("author", "unknown"), q.get("theme", args.theme), out)
        if audio_file:
            final_out = out.replace(".mp4", "_audio.mp4")
            merge_audio(out, audio_file, final_out, duration=DURATION)
            # Remove the silent version
            if os.path.exists(out) and os.path.exists(final_out):
                os.remove(out)
            print(f"Done -> {final_out}")
        else:
            print(f"Done -> {out}")


if __name__ == "__main__":
    main()