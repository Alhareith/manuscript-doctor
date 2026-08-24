from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'evaluation' / 'input'
OUT = ROOT / 'evaluation' / 'demo_showcase'
OUT.mkdir(parents=True, exist_ok=True)
NAMES = [
    '01_handwritten_legal_parchment.jpg',
    '02_handwritten_book_pages.jpg',
    '03_handwritten_dense_letter.jpg',
    '04_handwritten_fine_script.jpg',
    '05_printed_newspaper_aged_page1.jpg',
    '07_printed_newspaper_mixed_layout.jpg',
    '08_arabic_printed_newspaper_page1.jpg',
    '10_printed_newspaper_degraded_column.jpg',
    'boundary_test_011.jpg',
    'b01.jpg',
    'b02.jpg',
    '11_skewed.jpg',
]
thumb_w, thumb_h = 300, 240
label_h = 44
cols = 3
rows = (len(NAMES) + cols - 1) // cols
sheet = Image.new('RGB', (cols * thumb_w, rows * (thumb_h + label_h)), '#f7f4ed')
draw = ImageDraw.Draw(sheet)
for i, name in enumerate(NAMES):
    path = SRC / name
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((thumb_w - 20, thumb_h - 20), Image.Resampling.LANCZOS)
        tile = Image.new('RGB', (thumb_w, thumb_h), 'white')
        x = (thumb_w - image.width) // 2
        y = (thumb_h - image.height) // 2
        tile.paste(image, (x, y))
    col, row = i % cols, i // cols
    x0, y0 = col * thumb_w, row * (thumb_h + label_h)
    sheet.paste(tile, (x0, y0))
    draw.rectangle((x0, y0 + thumb_h, x0 + thumb_w, y0 + thumb_h + label_h), fill='#263238')
    draw.text((x0 + 8, y0 + thumb_h + 7), name[:38], fill='white')
sheet.save(OUT / 'candidate_contact_sheet.jpg', quality=92)
print(OUT / 'candidate_contact_sheet.jpg')
