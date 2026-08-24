from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation' / 'extended_qa' / 'input'
OUT.mkdir(parents=True, exist_ok=True)


def save(name, image, ext=None):
    path = OUT / name
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    suffix = ext or path.suffix.lower()
    params = []
    if suffix in {'.jpg', '.jpeg'}:
        params = [cv2.IMWRITE_JPEG_QUALITY, 92]
    if not cv2.imwrite(str(path), image, params):
        raise RuntimeError(f'could not save {path}')


def page(width, height, color=False):
    if color:
        canvas = np.full((height, width, 3), (245, 240, 225), dtype=np.uint8)
        paper = (255, 255, 255)
        ink = (40, 65, 130)
    else:
        canvas = np.full((height, width), 238, dtype=np.uint8)
        paper = 255
        ink = 24
    margin_x = max(5, width // 8)
    margin_y = max(5, height // 8)
    cv2.rectangle(canvas, (margin_x, margin_y), (width - margin_x, height - margin_y), paper, -1)
    scale = max(0.25, min(width / 900.0, height / 650.0))
    thickness = max(1, int(round(3 * scale)))
    font_scale = max(0.25, 1.0 * scale)
    cv2.putText(canvas, 'DOCUMENT QA', (max(8, margin_x + int(35 * scale)), max(24, margin_y + int(65 * scale))), cv2.FONT_HERSHEY_SIMPLEX, font_scale, ink, thickness, cv2.LINE_AA)
    for index in range(5):
        y = margin_y + int((145 + index * 55) * scale)
        cv2.line(canvas, (max(8, margin_x + int(35 * scale)), y), (width - margin_x - int(35 * scale), y), ink, thickness, cv2.LINE_AA)
    cv2.rectangle(canvas, (width - margin_x - int(150 * scale), height - margin_y - int(75 * scale)), (width - margin_x - int(35 * scale), height - margin_y - int(20 * scale)), ink, thickness)
    return canvas


sizes = [(32, 24), (64, 48), (160, 120), (320, 240), (640, 480), (900, 650), (1200, 900), (2000, 1500), (3000, 2000)]
for index, (width, height) in enumerate(sizes):
    save(f'valid_{index:02d}_{width}x{height}_gray.png', page(width, height, False))

save('valid_color_900x650.jpg', page(900, 650, True))
save('valid_color_1200x900.jpeg', page(1200, 900, True))

base = page(900, 650, False)
save('bright.png', cv2.convertScaleAbs(base, alpha=0.35, beta=165))
save('dark.png', cv2.convertScaleAbs(base, alpha=0.42, beta=0))
save('low_contrast.png', cv2.convertScaleAbs(base, alpha=0.2, beta=120))
save('blurred.jpg', cv2.GaussianBlur(base, (0, 0), 8))

rng = np.random.default_rng(20260822)
noise = rng.normal(0, 38, base.shape).astype(np.float32)
save('high_noise.png', base.astype(np.float32) + noise)

for angle in (-15, -5, 5, 15):
    matrix = cv2.getRotationMatrix2D((450, 325), angle, 1.0)
    rotated = cv2.warpAffine(base, matrix, (900, 650), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    save(f'skew_{angle:+d}deg.png', rotated)

# Deliberately uniform and high-frequency cases for threshold and denoising boundaries.
save('uniform_white.png', np.full((480, 640), 255, dtype=np.uint8))
save('uniform_black.png', np.zeros((480, 640), dtype=np.uint8))
checker = np.indices((480, 640)).sum(axis=0) % 2 * 255
save('checkerboard.png', checker.astype(np.uint8))

gradient = np.tile(np.linspace(0, 255, 1000, dtype=np.uint8), (700, 1))
save('gradient.png', gradient)

# A clear boundary and a perspective-distorted page.
framed = np.full((700, 1000, 3), (35, 40, 48), dtype=np.uint8)
cv2.rectangle(framed, (150, 80), (850, 620), (250, 250, 245), -1)
cv2.rectangle(framed, (150, 80), (850, 620), (5, 5, 5), 6)
cv2.putText(framed, 'CLEAR DOCUMENT', (260, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 4, cv2.LINE_AA)
for y in range(280, 540, 55):
    cv2.line(framed, (230, y), (770, y), (20, 20, 20), 4)
save('clear_boundary.jpg', framed)

source = page(620, 850, False)
quad = np.float32([[0, 0], [849, 0], [849, 619], [0, 619]])
dst = np.float32([[55, 25], [790, 80], [820, 575], [25, 600]])
perspective = cv2.warpPerspective(source, cv2.getPerspectiveTransform(quad, dst), (850, 620), borderValue=80)
save('perspective.jpg', perspective)

# Valid PNG with an alpha channel: useful for upload/read normalization checks.
rgba = cv2.cvtColor(page(640, 480, True), cv2.COLOR_BGR2BGRA)
rgba[:, :, 3] = 230
save('color_alpha.png', rgba)

# Unsupported format for negative upload tests.
webp_path = OUT / 'unsupported.webp'
cv2.imwrite(str(webp_path), page(320, 240, True), [cv2.IMWRITE_WEBP_QUALITY, 85])

manifest = []
for path in sorted(OUT.iterdir()):
    data = path.read_bytes()
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    manifest.append({
        'name': path.name,
        'suffix': path.suffix.lower(),
        'bytes': len(data),
        'shape': None if image is None else list(image.shape),
        'mean': None if image is None else float(image.mean()),
        'min': None if image is None else int(image.min()),
        'max': None if image is None else int(image.max()),
    })
(ROOT / 'evaluation' / 'extended_qa' / 'manifest.json').write_text(__import__('json').dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'generated {len(manifest)} QA files at {OUT}')
