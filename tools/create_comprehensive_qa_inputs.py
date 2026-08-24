from pathlib import Path
import cv2
import numpy as np

ROOT = Path('/home/ubuntu/image_project_split')
OUT = ROOT / 'evaluation' / 'comprehensive_qa' / 'input'
OUT.mkdir(parents=True, exist_ok=True)


def save(name: str, image: np.ndarray) -> None:
    path = OUT / name
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f'failed to write {path}')


def base_page(color=False, size=(900, 650)):
    h, w = size[1], size[0]
    if color:
        canvas = np.full((h, w, 3), (248, 245, 235), dtype=np.uint8)
        cv2.rectangle(canvas, (100, 80), (w - 100, h - 80), (255, 255, 255), -1)
        ink = (55, 70, 130)
    else:
        canvas = np.full((h, w), 245, dtype=np.uint8)
        cv2.rectangle(canvas, (100, 80), (w - 100, h - 80), 255, -1)
        ink = 25
    cv2.putText(canvas, 'DOCUMENT QA SAMPLE', (145, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.1, ink, 3, cv2.LINE_AA)
    for y, width in [(230, 570), (280, 620), (330, 520), (380, 600), (430, 450)]:
        cv2.line(canvas, (145, y), (145 + width, y), ink, 4, cv2.LINE_AA)
    cv2.rectangle(canvas, (590, 470), (730, 540), ink, 4)
    return canvas


normal = base_page(False)
save('01_normal_grayscale.png', normal)
save('02_normal_color.png', base_page(True))
save('03_very_bright.png', cv2.convertScaleAbs(normal, alpha=0.45, beta=140))
save('04_dark.png', cv2.convertScaleAbs(normal, alpha=0.45, beta=5))
save('05_low_contrast.png', cv2.convertScaleAbs(normal, alpha=0.28, beta=92))

rng = np.random.default_rng(20260822)
noise = rng.normal(0, 30, normal.shape).astype(np.float32)
save('06_high_noise.png', normal.astype(np.float32) + noise)

blurred = cv2.GaussianBlur(normal, (0, 0), 5)
save('07_blurred.png', blurred)

for angle in (2, 5, 10, -7):
    matrix = cv2.getRotationMatrix2D((normal.shape[1] / 2, normal.shape[0] / 2), angle, 1.0)
    rotated = cv2.warpAffine(normal, matrix, (normal.shape[1], normal.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    save(f'08_skew_{angle:+d}deg.png', rotated)

# A page-like image with a clear border for preparation/crop validation.
framed = np.full((700, 1000, 3), (40, 45, 50), dtype=np.uint8)
cv2.rectangle(framed, (155, 95), (845, 605), (248, 248, 245), -1)
cv2.rectangle(framed, (155, 95), (845, 605), (10, 10, 10), 5)
cv2.putText(framed, 'FRAMED DOCUMENT', (245, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 4, cv2.LINE_AA)
for y in range(285, 500, 55):
    cv2.line(framed, (235, y), (765, y), (30, 30, 30), 4)
save('09_clear_document_boundary.jpg', framed)

# Mild perspective distortion with a non-white background.
source = base_page(False, (620, 850))
quad = np.float32([[0, 0], [849, 0], [849, 619], [0, 619]])
dst = np.float32([[70, 30], [790, 80], [820, 570], [30, 600]])
perspective = cv2.warpPerspective(source, cv2.getPerspectiveTransform(quad, dst), (850, 620), borderValue=100)
save('10_perspective_page.jpg', perspective)

# Copy/link references are represented in the manifest; leave originals untouched.
references = [
    ROOT / 'evaluation' / 'input' / 'b01.jpg',
    ROOT / 'evaluation' / 'input' / 'b02.jpg',
]
manifest = []
for path in sorted(OUT.iterdir()):
    if path.is_file():
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        manifest.append(f'{path.name}\tshape={tuple(image.shape)}\tmean={float(image.mean()):.3f}\tmin={int(image.min())}\tmax={int(image.max())}')
for path in references:
    if path.exists():
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        manifest.append(f'REAL::{path.name}\tshape={tuple(image.shape)}\tmean={float(image.mean()):.3f}\tmin={int(image.min())}\tmax={int(image.max())}')
(OUT.parent / 'manifest.tsv').write_text('\n'.join(manifest) + '\n', encoding='utf-8')
print(f'created {len(list(OUT.iterdir()))} files in {OUT}')
print((OUT.parent / 'manifest.tsv').read_text(encoding='utf-8'))
