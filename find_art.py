#!/usr/bin/env python3
"""Find the original art for Hearthcards custom cards.

For each card image in a range: crop the art window (with a safety margin so
no frame or card edge is included), upload the crop to Google Lens reverse
image search, and save the resulting search link.

Usage:
  python3 find_art.py CARDS_DIR --start "1 HSneucre10ColossusOfTheSun.png" \
      --end "1 HSwrlwea4AxeFel.png" --out results

Outputs (in --out):
  crops/NNN_<card>.jpg   the cropped art that was searched
  links.txt              ordered list: one Google results link per card
  links.tsv              index, card file, link
  links_by_url.txt       (with --crops-base-url) permanent Lens links that
                         search the crop by its public URL, e.g. after the
                         crops are pushed to a public GitHub repo
"""
import argparse
import csv
import os
import re
import sys
import time
import urllib.parse

import requests
from PIL import Image

# Crop boxes (left, top, right, bottom) in pixels for each Hearthcards layout,
# keyed by (card type code, image size). Boxes sit inside the art window with
# a margin of ~10-15px, so they never touch the frame, gems, dragon or banner.
LAYOUTS = {
    # Minion: oval window. Box is the rectangle inscribed in the oval, minus a margin.
    ("cre", (785, 1100)): (270, 180, 540, 500),
    # Spell: rectangular window with rounded corners; box clears the corners.
    ("spe", (785, 1100)): (180, 200, 635, 515),
    # Legendary spell: same window, dragon covers the top-left of it.
    ("spe", (825, 1100)): (180, 215, 635, 515),
    # Location: arched window.
    ("loc", (795, 1120)): (175, 205, 665, 545),
    # Weapon: round window. Inscribed square minus a margin.
    ("wea", (785, 1070)): (270, 195, 540, 465),
}

LENS_URL = "https://lens.google.com/v3/upload"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def card_type(name):
    # Names look like "1 HS<class:3><type:3><cost><Name>.png", e.g. HSneucre10...
    m = re.match(r"\d+ HS[a-z]{3}([a-z]{3})", name)
    return m.group(1) if m else None


def crop_art(path):
    im = Image.open(path)
    key = (card_type(os.path.basename(path)), im.size)
    if key not in LAYOUTS:
        raise ValueError(f"unknown layout {key} for {path}")
    art = im.crop(LAYOUTS[key])
    if art.mode in ("RGBA", "LA", "P"):
        art = art.convert("RGBA")
        bg = Image.new("RGB", art.size, "white")
        bg.paste(art, mask=art.split()[-1])
        art = bg
    return art.convert("RGB")


def lens_search(jpg_path, session, retries=4):
    """Upload an image to Google Lens and return the results page URL."""
    for attempt in range(retries):
        try:
            with open(jpg_path, "rb") as f:
                r = session.post(
                    LENS_URL,
                    params={"hl": "en", "re": "df", "ep": "gsbubb",
                            "st": str(int(time.time() * 1000))},
                    files={"encoded_image": (os.path.basename(jpg_path), f, "image/jpeg")},
                    allow_redirects=False, timeout=60)
            loc = r.headers.get("Location", "")
            if r.status_code in (302, 303) and "google.com/search" in loc:
                return loc
            raise RuntimeError(f"HTTP {r.status_code}, Location={loc[:120]!r}")
        except Exception as e:  # network error, captcha, etc.
            wait = 2 ** (attempt + 1)
            print(f"  retry {attempt + 1} in {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Lens upload failed for {jpg_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards_dir")
    ap.add_argument("--start", required=True, help="first card file name (inclusive)")
    ap.add_argument("--end", required=True, help="last card file name (inclusive)")
    ap.add_argument("--out", default="results")
    ap.add_argument("--crop-only", action="store_true", help="only crop, skip search")
    ap.add_argument("--crops-base-url", help="public URL of the crops folder; "
                    "writes links_by_url.txt with permanent Lens links")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between searches")
    args = ap.parse_args()

    # Byte order sort = the order GitHub lists the files in this repo.
    files = sorted(f for f in os.listdir(args.cards_dir) if f.lower().endswith(".png"))
    i, j = files.index(args.start), files.index(args.end)
    cards = files[i:j + 1]
    print(f"{len(cards)} cards: {cards[0]} .. {cards[-1]}")

    crops_dir = os.path.join(args.out, "crops")
    os.makedirs(crops_dir, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA

    rows = []
    for n, name in enumerate(cards, 1):
        stem = os.path.splitext(name)[0].removeprefix("1 ")
        jpg = os.path.join(crops_dir, f"{n:03d}_{stem}.jpg")
        crop_art(os.path.join(args.cards_dir, name)).save(jpg, quality=95)
        link = ""
        if not args.crop_only:
            link = lens_search(jpg, session)
            time.sleep(args.delay)
        rows.append((n, name, link, os.path.basename(jpg)))
        print(f"{n:3d} {name} {link[:80]}")

    if args.crops_base_url:
        base = args.crops_base_url.rstrip("/") + "/"
        with open(os.path.join(args.out, "links_by_url.txt"), "w") as f:
            for r in rows:
                img = base + urllib.parse.quote(r[3])
                f.write("https://lens.google.com/uploadbyurl?url="
                        + urllib.parse.quote(img, safe="") + "\n")
    if not args.crop_only:
        with open(os.path.join(args.out, "links.txt"), "w") as f:
            f.write("\n".join(r[2] for r in rows) + "\n")
        with open(os.path.join(args.out, "links.tsv"), "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["#", "card", "google_results_link"])
            w.writerows(r[:3] for r in rows)


if __name__ == "__main__":
    main()
