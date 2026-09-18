# Text-Line → Curvature → Mesh Dewarping — Final Experimental Gate

> Research branch only. Nothing in this experiment is wired into `master`, `app.py`, the production registry, or the UI.

## Final acceptance rule

A dewarping case is accepted only when **both** conditions are satisfied:

1. Text-line curvature RMS is reduced by **at least 70%**.
2. Text structure is preserved with tolerant binary-stroke **F1 ≥ 0.90**.

Additional safety rules:

- A flat document must be detected as already flat and left unchanged; its structure F1 must remain **≥ 0.98**.
- A sparse/no-text document must **abstain** instead of inventing a deformation field.

The structure metric compares dark-stroke masks with a 2 px spatial tolerance, so a result cannot pass merely because lines become straighter while text strokes move, disappear, or distort.

## Controlled V1 result

These values come from the isolated deterministic 900×1200 experiment fixture and the current prototype implementation.

| Case | Status | Curvature RMS before → after | Reduction | Structure F1 | Final gate |
| --- | --- | ---: | ---: | ---: | --- |
| Warped document / multi-wave | Applied | 2.413 → 1.044 | **56.7%** | **0.141** | **FAIL** |
| Curved book-like page | Applied | 7.937 → 2.608 | **67.1%** | **0.279** | **FAIL** |
| Already-flat document | No-op | 0.000 → 0.000 | 100% no-op | **1.000** | **PASS** |
| Sparse-text document | Incorrectly applied | 12.274 → detector unavailable after warp | not valid | 0.931 | **FAIL** |

## What still fails

### 1. Warped multi-wave document
It fails both gates:
- curvature reduction is below 70%;
- structural fidelity is far below 0.90.

This indicates the current independent strip matching can switch or misalign text lines and then create a destructive dense field.

### 2. Curved book-like page
It is close on curvature but still fails:
- 67.1% reduction is below the 70% requirement;
- F1 0.279 is unacceptable, so the page may look flatter while text geometry is not preserved accurately enough.

### 3. Sparse-text document
The detector should abstain, but it finds enough false/duplicate line tracks to apply a warp. This is a safety failure regardless of the output appearance.

### 4. Already-flat document
This is the only case that currently passes the final rule. The detector returns `already_flat` and does not modify the image.

## Engineering conclusion

**Final gate: FAIL. Production integration remains blocked.**

The next prototype must replace independent per-strip peak matching with continuity-aware baseline tracking and add explicit line-count/coverage/track-uniqueness confidence. The dense mesh must only be generated from stable non-crossing line tracks. The same four final gates must then be re-run unchanged.
