# Hearthcards_Script

## find_art.py — find original art for Hearthcards cards

Crops the art window of each card (with a safety margin, so no frame or card
edge is included), uploads the crop to Google Lens reverse image search and
saves the results link. Supports minions, spells (normal + legendary),
weapons and locations in the standard Hearthcards export sizes.

```
pip install pillow requests
git clone https://github.com/ALDRAFTCUSTOM/DRAFT_2026
python3 find_art.py DRAFT_2026 \
  --start "1 HSneucre10ColossusOfTheSun.png" \
  --end "1 HSwrlwea4AxeFel.png" --out results
```

Output: `results/links.txt` (one link per card, in order),
`results/links.tsv` (number, card, link) and `results/crops/` (searched images).
Use `--crop-only` to check the crops without searching.
