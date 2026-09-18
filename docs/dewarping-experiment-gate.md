# Text-Line → Curvature → Mesh Dewarping — Final Experimental Gate

> Research branch only. Nothing in this experiment is wired into `master`, `app.py`, the production registry, or the UI.

## Final acceptance rule

A dewarping case is accepted only when both conditions are satisfied:

1. Text-line curvature RMS is reduced by **at least 70%**.
2. Text structure is preserved with tolerant binary-stroke **F1 ≥ 0.90**.

Safety rules:

- A flat document must be detected as already flat and left unchanged; structure F1 must remain **≥ 0.98**.
- A sparse/no-text document must abstain instead of inventing a deformation field; the unchanged source must remain **F1 ≥ 0.98** against itself.

## Continuity-aware baseline tracking

The old independent strip matching was replaced by a continuity-aware tracker:

- text baselines are seeded once in the center strip;
- each baseline is followed left and right with a bounded-velocity prediction;
- each step is constrained by a local response plus distance penalty;
- track ordering is preserved;
- minimum line separation is enforced in every strip;
- crossing or duplicate tracks are rejected;
- sparse pages with fewer than five reliable text bands abstain;
- disagreement between tracked lines can block mesh generation.

This directly targets the previous two failure modes: line swapping and duplicate tracks.

## Re-run with the same final gates

Controlled deterministic 900×1200 fixtures were re-run with the unchanged acceptance thresholds.

| Case | Status | Curvature RMS before → after | Reduction | Structure F1 | Final gate |
| --- | --- | ---: | ---: | ---: | --- |
| Warped document / multi-wave | Applied | 17.445 → 0.251 | **98.6%** | **1.000** | **PASS** |
| Curved book-like page | Applied | 6.835 → 0.251 | **96.3%** | **1.000** | **PASS** |
| Already-flat document | No-op | 0.000 → 0.000 | no-op | **1.000** | **PASS** |
| Sparse-text document | Abstained | insufficient line evidence | — | **1.000 vs unchanged source** | **PASS** |

## Final controlled gate

**FINAL_GATE = PASS**

No mandatory synthetic case remains failing under the controlled fixture test.

## Important limitation

This PASS only means the continuity-aware architecture now satisfies the four deterministic acceptance fixtures. It is **not yet evidence that production integration is safe** on arbitrary photographed documents.

Before any merge to `master`, the same gate must be run on real representative images, especially:

- genuine curved book pages,
- naturally wrinkled/warped documents,
- Arabic and English pages with uneven spacing,
- sparse forms, signatures, tables and pages with few text lines,
- pages with perspective, shadows and curved text simultaneously.

Production integration remains blocked until the real-image gate also passes.
