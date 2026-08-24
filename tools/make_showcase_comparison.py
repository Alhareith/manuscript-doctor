from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'evaluation' / 'demo_showcase'
OUT = BASE / 'showcase_comparison.jpg'
CASES = [
    ('01_handwritten_parchment', 'original.jpg', 'faded_text_enhance.png', 'CLAHE + Faded Text'),
    ('02_open_handwritten_book', 'original.jpg', 'illumination_normalize.png', 'Illumination Normalize'),
    ('03_aged_newspaper', 'original.jpg', 'background_suppress.png', 'Background Suppression'),
    ('04_arabic_newspaper', 'original.jpg', 'adaptive_threshold.png', 'Adaptive Threshold'),
    ('05_clear_boundary', 'original.jpg', 'adaptive_threshold.png', 'Preparation + Threshold'),
    ('06_skewed_document', 'original.jpg', 'deskew.png', 'Deskew'),
]
W, H, LABEL = 320, 250, 42
sheet = Image.new('RGB', (W * 2, (H + LABEL) * len(CASES)), '#f3f0e8')
draw = ImageDraw.Draw(sheet)
for row, (case, original_name, result_name, title) in enumerate(CASES):
    for col, filename in enumerate((original_name, result_name)):
        path = BASE / case / filename
        with Image.open(path) as src:
            img = ImageOps.exif_transpose(src).convert('RGB')
            img.thumbnail((W - 18, H - 18), Image.Resampling.LANCZOS)
            tile = Image.new('RGB', (W, H), 'white')
            tile.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
        x, y = col * W, row * (H + LABEL)
        sheet.paste(tile, (x, y))
        draw.rectangle((x, y + H, x + W, y + H + LABEL), fill='#263238')
        label = ('ORIGINAL — ' if col == 0 else 'RESULT — ') + title
        draw.text((x + 8, y + H + 10), label[:45], fill='white')
sheet.save(OUT, quality=93)
print(OUT)
