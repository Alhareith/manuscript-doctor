# Text-Line → Curvature → Mesh Dewarping — Experimental Gate

> Research branch only. This feature is **not** wired into `master`, `app.py`, the operation registry, or the UI.

## Mandatory acceptance gates

The candidate must pass all four cases before production integration:

| Case | Required behavior |
| --- | --- |
| Warped document | Reduce measured text-line curvature by at least 70% without destructive text deformation |
| Curved book page | Reduce measured text-line curvature by at least 70% without destructive text deformation |
| Already-flat document | No-op; do not warp an already-straight page |
| Sparse/no text | Abstain; do not guess a deformation field without enough line evidence |

## Prototype V0 result

Controlled 900×1200 fixtures were used only to validate the architecture before any production integration.

| Case | Result | RMS curvature before → after | Gate |
| --- | --- | ---: | --- |
| Warped document / multi-wave | Applied | 5.07 → 3.27 | **FAIL** — reduction is not sufficient |
| Curved book-like page | Applied | 5.96 → 1.47 | **PASS on curvature only** |
| Already-flat document | No-op | 0.00 → 0.00 | **PASS** |
| Sparse text | Abstained | insufficient line evidence | **PASS** |

The current detector therefore remains experimental. In particular, the multi-wave case shows that line correspondence across vertical strips is not yet robust enough. Production integration is blocked.

## Next experiment

Replace independent per-strip peak matching with continuity-aware baseline tracking:

1. detect candidate text bands,
2. track each baseline left-to-right with a bounded displacement model,
3. reject line swaps and duplicate tracks,
4. estimate a confidence score from track coverage and agreement,
5. build the dense mesh only when confidence is sufficient,
6. add a structural-fidelity gate so curvature improvement alone can never approve a destructive warp.

The existing Smart Pipeline and document preparation remain unchanged until these gates pass.
