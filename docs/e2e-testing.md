# Manuscript Doctor — End-to-End Validation

## Test Environment

- Date:
- OS:
- Python:
- Flask:
- OpenCV:
- Browser:

---

## Automated Validation

Command:

`python -m pytest tests/test_end_to_end.py -q`

Result:

- Passed:
- Failed:

Full Suite:

`python -m pytest -q`

Result:

- Passed:
- Failed:

---

## Test Status Values

- PASS
- FAIL
- KNOWN LIMITATION
- NOT APPLICABLE

---

# Real Image Validation

## 01 — Normal Document

Image:

`01_normal.jpg`

Checks:

- [ ] Upload successful
- [ ] Original displayed
- [ ] Examination values displayed
- [ ] Diagnosis displayed correctly
- [ ] Preservation Profile displayed
- [ ] Smart Pipeline executes
- [ ] Decision displayed
- [ ] Result displayed
- [ ] Download works

Observed Decision:

Result:

Status:

---

## 02 — Dark Document

Image:

`02_dark.jpg`

Checks:

- [ ] Darkness diagnosis appears
- [ ] Recommendation is logical
- [ ] CLAHE uses conservative settings when recommended
- [ ] Smart Pipeline executes
- [ ] Preservation Verification runs
- [ ] Original remains unchanged

Result:

Status:

---

## 03 — Low Contrast

Image:

`03_low_contrast.jpg`

Checks:

- [ ] Low contrast diagnosed
- [ ] CLAHE recommended
- [ ] clip_limit = 1.5
- [ ] tile_grid_size = 8
- [ ] Smart Pipeline executes
- [ ] Result displayed
- [ ] Preservation result displayed

Result:

Status:

---

## 04 — Noise

Image:

`04_noisy.jpg`

Checks:

- [ ] Current Noise Metric value recorded
- [ ] Actual visual noise reviewed
- [ ] Median recommendation behavior recorded
- [ ] Median is not automatically executed by Smart Pipeline
- [ ] No claim that noise is completely removed

Noise Metric:

Observed visual noise:

Pipeline behavior:

Status:

---

## 05 — Uneven Illumination

Image:

`05_uneven_lighting.jpg`

Checks:

- [ ] Uneven illumination diagnosed
- [ ] Recommendation displayed
- [ ] Adaptive Threshold remains Binarization
- [ ] Binary Candidate separate from primary result
- [ ] Candidate marked review_required

Status:

---

## 06 — Fine Details

Image:

`06_fine_details.jpg`

Checks:

- [ ] Preservation sensitivity displayed
- [ ] Original available for comparison
- [ ] Sharpen 0.25 tested manually
- [ ] Thin details reviewed
- [ ] No obvious strong halos
- [ ] Preservation warnings visible

Visual observation:

Status:

---

## 07 — Bleed-through Boundary Case

Image:

`07_bleed_through.jpg`

Checks:

- [ ] Image uploads and analyzes normally
- [ ] System does not claim dedicated bleed-through diagnosis
- [ ] System does not claim bleed-through removal
- [ ] Enhancement behavior reviewed visually
- [ ] Limitation remains explicit

Visual observation:

Status:

---

# Manual Operations

## CLAHE

Parameters:

- clip_limit: 1.5
- tile_grid_size: 8

Checks:

- [ ] HTTP success
- [ ] Result displayed
- [ ] Result PNG
- [ ] Preservation returned
- [ ] Original unchanged
- [ ] Download works

Status:

---

## Histogram Equalization

Checks:

- [ ] Manual execution works
- [ ] Result displayed
- [ ] Preservation returned
- [ ] Not automatically promoted as safe

Status:

---

## Median Denoising

Parameters:

- kernel_size: 3

Checks:

- [ ] Manual execution works
- [ ] Result displayed
- [ ] Original unchanged
- [ ] Preservation returned

Status:

---

## Sharpen

Parameters:

- amount: 0.25
- kernel_size: 3

Checks:

- [ ] Manual execution works
- [ ] Result displayed
- [ ] Preservation returned

Status:

---

## Global Threshold

Parameters:

- threshold: 127

Checks:

- [ ] Manual execution works
- [ ] Binary output generated
- [ ] No automatic quality claim

Status:

---

## Otsu Threshold

Checks:

- [ ] Manual execution works
- [ ] Binary output generated

Status:

---

## Adaptive Threshold

Parameters:

- block_size: 35
- c: 11

Checks:

- [ ] Manual execution works
- [ ] Binary output generated

Status:

---

## Morphological Opening

Parameters:

- kernel_size: 3

Checks:

- [ ] Manual execution works
- [ ] Preservation returned

Status:

---

## Morphological Closing

Parameters:

- kernel_size: 3

Checks:

- [ ] Manual execution works
- [ ] Preservation returned

Status:

---

# Invalid Inputs

## Unsupported Extension

Expected:

`UNSUPPORTED_FILE_TYPE`

Status:

---

## Corrupt Image

Expected:

`UNREADABLE_IMAGE`

Status:

---

## 16-bit Image

Expected:

`UNSUPPORTED_IMAGE_DEPTH`

Status:

---

## Invalid Operation

Expected:

`INVALID_OPERATION`

Status:

---

## Invalid Parameters

Expected:

`INVALID_OPERATION_PARAMETERS`

Status:

---

## Invalid Image ID

Expected:

`INVALID_IMAGE_ID`

Status:

---

## Unknown Image ID

Expected:

`IMAGE_NOT_FOUND`

Status:

---

## Invalid Result ID

Expected:

`INVALID_RESULT_ID`

Status:

---

## Unknown Result ID

Expected:

`RESULT_NOT_FOUND`

Status:

---

# Runtime State

## Sequential Manual Results

Flow:

`CLAHE → Sharpen`

Checks:

- [ ] Each operation receives a new result ID
- [ ] Latest result replaces previous UI result
- [ ] Download uses latest result

Status:

---

## Manual → Smart Pipeline

Checks:

- [ ] Previous result UI cleared before Smart execution
- [ ] Smart result becomes primary result
- [ ] Download uses Smart result

Status:

---

## Start Over

Checks:

- [ ] Selected document cleared
- [ ] imageId cleared
- [ ] resultId cleared
- [ ] Metrics cleared
- [ ] Diagnoses cleared
- [ ] Recommendations cleared
- [ ] Results cleared
- [ ] Binary Candidates cleared
- [ ] Download disabled
- [ ] Manual operation reset

Status:

---

## Browser Refresh

Checks:

- [ ] No crash
- [ ] No stale result restored incorrectly
- [ ] Initial UI state restored

Status:

---

# Desktop Test

Checks:

- [ ] Upload works
- [ ] Examination works
- [ ] Manual Treatment works
- [ ] Smart Treatment works
- [ ] Comparison works
- [ ] Download works
- [ ] No unexpected layout overflow

Status:

---

# Mobile 375px Test

Checks:

- [ ] No horizontal scroll
- [ ] Upload works
- [ ] Metrics readable
- [ ] Manual controls usable
- [ ] Smart Pipeline button usable
- [ ] Comparison fits viewport
- [ ] Result image fits viewport
- [ ] Download works

Status:

---

# Browser Console

Checks:

- [ ] No JavaScript errors during Upload
- [ ] No JavaScript errors during Manual Treatment
- [ ] No JavaScript errors during Smart Pipeline
- [ ] No JavaScript errors during Download

Status:

---

# Network Safety

Checks:

- [ ] No local filesystem paths sent by frontend
- [ ] No local filesystem paths returned in API JSON
- [ ] Requests use image IDs
- [ ] Requests use result IDs
- [ ] No Python stack traces visible to user

Status:

---

# Original Immutability

Test:

1. Upload document.
2. Run CLAHE.
3. Run Sharpen.
4. Run Morphological Closing.
5. Run Smart Pipeline.
6. Retrieve original again.

Checks:

- [ ] Original remains visually unchanged
- [ ] Stored original bytes remain unchanged

Status:

---

# Scientific Integrity

- [ ] No claim of historical content restoration
- [ ] No claim of reconstruction of missing letters
- [ ] No preservation percentage
- [ ] No claim that structural change proves text loss
- [ ] Smart Pipeline described as Rule-Based
- [ ] No Machine Learning claim
- [ ] Bleed-through limitation remains explicit
- [ ] Binarization remains separate from Enhancement
- [ ] Preservation Verification described as heuristic
- [ ] Original remains the primary reference

---

# Known Limitations

## Noise Indicator

The current Noise Indicator requires additional validation before automatic denoising is enabled.

## Preservation Thresholds

Current Preservation thresholds remain provisional and require broader calibration.

## Bleed-through

Dedicated bleed-through diagnosis and suppression are not implemented in the current MVP.

## Generalization

The current evaluation images do not establish universal performance across manuscript collections.

---

# Final Phase 15 Decision

Decision:

`TBD`

Allowed:

- PASS
- PASS WITH KNOWN LIMITATIONS
- FAIL

Core workflow failures require `FAIL`.