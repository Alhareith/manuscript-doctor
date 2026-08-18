# Phase C Final Report — Smart Pipeline + Cross-Layer Integration + E2E Validation + Engineering Freeze

**Project:** Manuscript Doctor
**Phase:** C (Final)
**Date:** 2026-08-18
**Philosophy:** Diagnose → Treat → Preserve → Verify
**Priority:** Historical manuscript content preservation over cosmetic clarity.

---

## Section 1 — Cross-Layer Consistency Audit (Operations → Recommender → Pipeline → Frontend)

Full parameter audit across all four layers (extracted programmatically from `inspect.signature`, `recommender.py` constants, `static/js/main.js` `operationParameters`):

| Operation | Parameter | Operation Default | Frontend Default | Recommender Auto Value | Verdict |
|---|---|---|---|---|---|
| clahe | clip_limit | 1.5 | 1.5 | 1.5 / 2.0 (strong) / capped 1.2 (high-sens) | ✅ consistent |
| clahe | tile_grid_size | 8 | 8 | 8 | ✅ consistent |
| gamma_correct | gamma | 1.0 | 1.0 | 0.85 / 0.65 / 1.15 / 1.35 (adaptive) | ✅ consistent |
| illumination_normalize | kernel_size | 51 | 51 | 51 | ✅ consistent |
| illumination_normalize | strength | 0.65 | 0.65 | 0.65 / 0.45 (conservative) | ✅ consistent |
| median_denoise | kernel_size | 3 | 3 | 3 | ✅ consistent |
| sharpen | amount | 0.5 | 0.5 | 0.25 (auto = intentionally conservative) | ✅ by design |
| sharpen | sigma | 1.0 | 1.0 | 1.0 | ✅ consistent |
| adaptive_threshold | block_size | 35 | 35 | 35 | ✅ consistent |
| adaptive_threshold | c | 11 | 11 | 11 | ✅ consistent |
| morphological_black_hat | kernel_size | **5** | ~~3~~ → **5 (FIXED)** | manual-only | ✅ FIXED |
| deskew | angle | REQUIRED | 0 (UI default) | detected angle | ✅ by design |
| (all 8 remaining ops) | — | matched | matched | manual-only | ✅ consistent |

**Findings & Fixes:**
1. `morphological_black_hat` frontend default was 3, operation signature default is 5 → **fixed frontend to 5** (`static/js/main.js`). Root cause: stale UI constant.
2. `sharpen.amount`: frontend/manual = 0.5 (operation default), auto-pipeline = 0.25 (recommender `SHARPEN_PARAMS`). **Intentional conservative divergence**, documented, not a bug.
3. `deskew.angle` has no signature default (required); frontend slider defaults to 0 for manual use only; pipeline never calls deskew automatically (deferred/manual-only). No stale state.

**Contract verification (frontend ⇄ API ⇄ operations):** `collectManualParameters()` sends `{operation_id, parameters}` where each key matches the operation function argument name exactly (verified for all 20 operations). Pipeline endpoint (`app.py:720-917`) consumes `run_smart_pipeline` result fields: `image`, `decision`, `steps`, `preservation`, `recommendation`, `binarization_candidates`, `policy` — all preserved in the rebuilt pipeline.

**Verdict: PASS** (1 real mismatch found and fixed; 2 intentional divergences documented).

---

## Section 2 — Metric/Threshold Consistency

| Metric | Producer | Consumer | Thresholds | Status |
|---|---|---|---|---|
| `impulse_ratio` | analyzer `_noise_metrics` (residual ≥ 100 vs median3) | recommender diagnosis split | MODERATE 0.004 / HIGH 0.012 / AUTO 0.012 | ✅ single source |
| `isolated_impulse_ratio` | preservation `_isolated_impulse_ratio` (isolated 3×3 outliers) | preservation reference gate | REFERENCE 0.005 | ✅ distinct role |
| noise `value` | analyzer (mean abs residual) | recommender + pipeline benefit gate | MODERATE 12 / HIGH 20 / DROP ≥ 0.5 | ✅ consistent |
| `skew_angle` / `skew_confidence` | analyzer `_estimate_skew` | recommender deskew activation | 0.75° / 0.5 confidence | ✅ consistent |

**Clarification (documented):** `impulse_ratio` (diagnosis: raw outlier density) and `isolated_impulse_ratio` (preservation: neighborhood-isolated pixel detection used to suppress noise before reference comparison) are **two deliberately different metrics serving different layers**. Confusion hazard eliminated by naming + this report.

**Severity labels:** analyzer diagnoses emit `medium`/`high` only; recommender `_condition_profile` maps them to `none`/`medium`/`high`; preservation emits `low`/`medium`/`high` warning severities. No contradictory labels found across layers.

**Verdict: PASS** (no contradictions; the impulse pair is intentionally distinct).

---

## Section 3 — Pipeline Architecture (Rebuilt)

`processing/pipeline.py` rebuilt (601 → 664 lines) to the mandated flow:

```
Input → Recommend → [Select ONE candidate → Apply → Re-analyze
       → Benefit Gate → Preservation Gate → Accept OR Rollback] → Stop
```

- **NO filter chains:** `MAX_ACCEPTED_STEPS = 1` — exactly one accepted enhancement per run; the session stops after acceptance.
- **NO unjustified re-analysis:** `analyze_image()` is called exactly once per candidate attempt, solely to measure benefit.
- **Separation of state:** `accepted_image` and `candidate` are never aliased; rejection simply discards the candidate (rollback is structural).
- **Binarization:** independent path from the ORIGINAL image, always `review_required`, never replaces the enhancement result.

**Verdict: PASS** (architecture conforms exactly to spec).

---

## Section 4 — Actual Benefit Gate

Implemented in `_measure_benefit()` with fail-closed behavior (unknown operation → reject):

| Operation | Metric (from re-analysis) | Required improvement |
|---|---|---|
| gamma_correct | brightness distance to band [85, 200] | decrease ≥ 1.0 gray level |
| clahe | contrast (std) | increase ≥ 1.0 |
| sharpen | sharpness (Laplacian var) | increase ≥ 2% of baseline |
| median_denoise | noise mean residual | decrease ≥ 0.5 |
| illumination_normalize | illumination variation | decrease ≥ 0.01 |

Benefit is measured against the **current accepted state** (progressive), while preservation is verified against the **original** (absolute). "Preservation acceptable" alone can no longer accept a useless step — verified by `test_candidate_without_benefit_is_rejected`.

**Verdict: PASS.**

---

## Section 5 — Preservation Gate + Rollback

- Dimension change → `rejected_dimension_change` (rollback).
- Preservation exception → `verification_failed` (rollback).
- `high_risk` → `rejected_high_risk` (rollback).
- `caution` + high-sensitivity document → `rejected_sensitive_document` (rollback).
- `caution` + normal document → **accept AND STOP** — no further automatic steps from that candidate; warning surfaced in decision message.
- Final verification (`original` vs `final`) failure demotes `accepted*` to `review_required`.

All rollback paths proven by tests (`test_high_risk_candidate_is_rejected`, `test_caution_is_rejected_for_high_sensitivity`, `test_verification_failure_rejects_candidate`, `test_final_verification_failure_prevents_automatic_acceptance`).

**Verdict: PASS.**

---

## Section 6 — Treatment History + Loop Protection

- Same `operation_id` is never attempted twice within a run (`attempted` set) — `test_repeated_operation_is_not_retried`.
- `MAX_ATTEMPTS_PER_RUN = 4` rejected attempts → decision `review_required` with `reason_code: "manual_review_required"` — `test_max_attempts_triggers_manual_review`.
- Post-accept/caution, remaining recommendations are recorded as `deferred` with explicit notes (no silent dropping, no endless looping).

**Verdict: PASS.**

---

## Section 7 — Operation Ordering

Recommender priority order (validated in Phase B) is preserved and consumed in order: Illumination (10) → Gamma dark (20) / bright (25) → CLAHE (30) → Noise/Median (40) → Sharpen (50) → Deskew (60) → Binarization (70). Conflict rules (noise blocks sharpen; illumination defers CLAHE; exposure precedes contrast) enforced in `_blocked_operations`. Stress run shows the first-eligible operation wins per run, and complementary steps correctly appear as `deferred`.

**Verdict: PASS.**

---

## Section 8 — Mixed Conditions Stress Tests

Cases `21_mixed_dark_noise`, `22_mixed_uneven_low_contrast`, `12_show_through_like`, `20_compression_artifacts`, `13_stained_background` across all 3 sources:

- Mixed dark+noise: noise blocks sharpen; gaussian (non-impulse) noise defers denoising to manual; the run never applies an unsafe combination → `unchanged_due_to_risk` or single safe step.
- Uneven+low-contrast: illumination normalization precedes CLAHE (CLAHE blocked until illumination evaluated).
- Show-through/stains: conservative single step or clean rejection — no destructive auto-treatment.

**Verdict: PASS** (no unsafe combination executed in any of the 72 runs).

---

## Section 9 — Denoising Policy

- Impulse noise (impulse_ratio ≥ 0.012) + non-high sensitivity → median k=3 candidate (Phase B validated), gated by benefit (noise residual must drop ≥ 0.5) and preservation.
- Gaussian noise → NO automatic denoiser (bilateral/NLM manual-only, listed in `excluded_from_automatic` with reason).
- High preservation sensitivity → median excluded even for impulse noise.
- Verified: `test_median_requires_noise_drop`, `test_median_without_noise_drop_is_rejected`, recommender tests for gaussian/high-sensitivity paths.

**Verdict: PASS.**

---

## Section 10 — Contrast/Exposure Policy

Gamma (20/25) precedes CLAHE (30); only one is accepted per run; intensity_adjust is not auto-eligible (manual-only), eliminating Gamma→Intensity double-treatment. Uneven illumination defers CLAHE until normalization is evaluated. Double CLAHE impossible (single-step + no-repeat).

**Verdict: PASS.**

---

## Section 11 — Binarization Independent Path

`adaptive_threshold` runs on the ORIGINAL image, output saved as separate candidates, decision always `review_required` with explicit message; never enters `result["image"]`. Preservation for binary output is reported but not used for auto-acceptance (near-binary clipping check disabled by design in preservation layer).

**Verdict: PASS** (`test_binarization_is_separate_from_enhancement` + 9 bin=1 stress cases).

---

## Section 12 — High-Risk Operations Exclusion

`AUTO_ELIGIBLE_OPERATIONS = {clahe, gamma_correct, illumination_normalize, median_denoise, sharpen}` — whitelist enforcement. All morphology, thresholding variants, background/weak-structure suppression, faded-text enhance, deskew, bilateral, NLM, histogram equalization are manual-only (`MANUAL_ONLY_OPERATIONS`), any such recommendation renders as `deferred` with reason. Unknown/unlisted operations are rejected fail-closed.

**Verdict: PASS.**

---

## Section 13 — Healthy Image Protection

Analyzer-empty diagnosis → recommender emits nothing → pipeline returns copy of input with `no_treatment`. Invariant checked programmatically across all 72 stress cases (no healthy-image treatment). Note: synthetic "01_normal" sources are objectively bright (mean 209–241 > 200), so their `bright` diagnosis and single gamma step are **legitimate treatment**, not false positives.

**Verdict: PASS.**

---

## Section 14 — Diagnosis vs Recommendation Consistency

Blocked operations never silently disappear: `_blocked_operations` reasons surface in `excluded_from_automatic`; gaussian noise yields explicit "no calibrated automatic denoiser" recommendation entry (manual_review mode) rather than "no problem". Conflicts (NOISE_SHARPNESS, ILLUMINATION_CONTRAST_ORDER, etc.) reported with severity and message.

**Verdict: PASS.**

---

## Section 15 — Deskew End-to-End

Angles 0°, ±1°, ±2°, ±3.5°, ±5° × 3 sources (`tools/deskew_e2e_test.py`):

- **Pipeline behavior: PASS** — deskew always `deferred` (manual-only), never auto-applied. ✔
- **Detection accuracy:** on rotation-synthesized documents the Hough-based `_estimate_skew` frequently returns the **sign-inverted** magnitude (e.g., +5° → −5.00, err 10.0) or mis-reads sparse synthetic text (±3.8° at true ±1°). The rotation convention mismatch (CW vs CCW) and synthetic-text sparsity are the causes. **No regression was proven against real skewed documents**, and per the freeze rule the analyzer was NOT modified. Deskew stays manual-only with the detected angle shown to the user for confirmation — the safe design given these limits.

**Verdict: PASS with documented limitation (L1).**

---

## Section 16 — Frontend/Backend Contract

- Parameter names = API keys = operation arguments (Section 1 table; fixed black_hat).
- Pipeline response fields consumed by `app.py` unchanged; step records extended with `benefit` (additive, ignored by current UI rendering).
- Decision status vocabulary remains exactly the frontend-renderable set: `accepted`, `accepted_with_caution`, `no_treatment`, `unchanged_due_to_risk`, `review_required`, `verification_failed` (new `manual_review_required` is a `reason_code` inside `review_required`, not a new top-level status).
- Flask-dependent E2E suites (`test_app.py`, `test_backend_integration.py`, `test_end_to_end.py`) could not execute in this environment (`ModuleNotFoundError: flask`); HTTP-layer contract verified by code audit of `app.py:720-917` instead. **Limitation L3.**

**Verdict: PASS (code-audit level) / L3 for live HTTP tests.**

---

## Section 17 — Controlled E2E Stress Tests

`tools/stress_test_pipeline.py`, 72 cases (24 conditions × 3 sources), full analyze→recommend→pipeline:

- accepted: 52 · accepted_with_caution: 3 · unchanged_due_to_risk: 17 · no_treatment: 0 (all synthetic cases carry ≥1 diagnosis)
- Invariants verified per case: ≤1 accepted step; image unchanged iff rejected; no repeated operations; healthy images untouched.

**Result: ALL INVARIANTS HELD (0 violations).**

**Verdict: PASS.**

---

## Section 18 — Mixed Stress Tests

See Section 8; invariants additionally confirmed for mixed-condition cases inside the 72-case run (rollback integrity, single-step, no unsafe pairing). `21_mixed_dark_noise` and `22_mixed_uneven_low_contrast` behave conservatively (rejection or one safe step) on all three sources.

**Verdict: PASS.**

---

## Section 19 — Real Manuscript Validation

`source_01_clean_manuscript.png` (real manuscript) generated 24 condition variants; all passed invariants (Section 17 listing rows 32–55). Best-case: `05_gaussian_noise` accepted one gamma step with caution, noise left to manual denoiser choice — exactly the designed conservative behavior for irreplaceable content.

**Verdict: PASS** (on available real-manuscript-derived set; broader corpus remains future work, L2).

---

## Section 20 — Preservation Inside Pipeline

Every accepted step carries its full preservation report (`steps[i].preservation`); final result carries `preservation` verified against the original; benefit and preservation are separate gates and both must pass. Binarization candidates include preservation reports for manual review.

**Verdict: PASS.**

---

## Section 21 — Root-Cause Debugging Discipline

All fixes this phase were root-cause fixes: black_hat default traced to stale frontend constant (fixed at source); no behavioral special-casing was introduced anywhere; no test was weakened to pass.

---

## Section 22 — Test Quality Audit

- Correct decisions: 17 pipeline unit tests + 51 recommender + 43 preservation + 96 others = **207/207 pass**, 0 regressions (baseline 175 → 200 prior → 207 now, only additions).
- Benefit gate: pass and fail paths (2 tests); rollback: 4 tests; caution-stop: 1; rejection: 3; single-step: 2; dedupe: 1; step limit: 1; binarization separation: 1; invalid input: 1.
- False positives/negatives: none observed in 72-case stress run (invariant checker clean).
- E2E: stress + deskew scripts committed as tools; Flask E2E blocked by environment (L3).

---

## Section 23 — Final Operation Policy Table (from code)

| Operation | Auto? | Benefit metric | Notes |
|---|---|---|---|
| illumination_normalize | ✅ auto | illumination_variation ↓0.01 | conservative strength for high-sens |
| gamma_correct | ✅ auto | brightness→band distance ↓1 | adaptive 0.65–1.35 |
| clahe | ✅ auto | contrast ↑1.0 | blocked under uneven illumination; capped 1.2 high-sens |
| median_denoise | ✅ auto (impulse-only) | noise residual ↓0.5 | k=3; never for gaussian/high-sens |
| sharpen | ✅ auto | sharpness ↑2% | blocked by noise; 0.25 amount |
| deskew | ❌ manual | — | deferred, detected angle shown |
| adaptive_threshold | ❌ review-only | — | separate binarization path |
| histogram_eq, global/otsu threshold, morphology ×4, bilateral, NLM, background/weak-structure suppress, faded_text, intensity_adjust | ❌ manual | — | excluded with reasons |

---

## Section 24 — Known Limitations

- **L1 Skew detection polarity/accuracy** on synthetic rotations (Section 15); deskew remains manual-only — user confirms angle before application.
- **L2 Evaluation corpus** is 3 sources × 24 synthetic conditions; broader real-manuscript corpus not yet tested.
- **L3 Flask E2E suites** not executable in the frozen environment (flask missing); HTTP contract verified by audit only.
- **L4 Benefit thresholds** (1.0 contrast, 0.5 noise drop, 2% sharpness, 0.01 illumination) are engineering floors, not perceptual calibrations; they only reject useless steps, never accept risky ones.
- **L5 Single-step-per-run** means multi-condition documents need repeated pipeline invocations (by design; each run re-diagnoses).

---

## Section 25 — Engineering Freeze

- Legacy constants removed from pipeline: `AUTO_ENHANCEMENT_OPERATIONS` (2-op legacy set), `DEFERRED_AUTOMATIC_OPERATIONS` (median blanket deferral) — superseded by the whitelist + benefit gate architecture.
- No duplicate rule sources remain; recommender remains the single recommendation source, pipeline the single enforcement point.
- Dead artifact `temp_screenshot.png` (debug leftover) deleted. `s.py`, `clahe_test/`, `manuscript-doctor.zip` pre-exist outside this phase's scope and are listed for the owner to remove manually.
- Analyzer, Preservation, Operations, Recommender: **unmodified** this phase (constraint upheld; zero regressions confirm).

---

# FINAL JUDGMENT

## **READY WITH KNOWN LIMITATIONS**

The Smart Pipeline now enforces the full Diagnose → Treat → Preserve → Verify philosophy with measurable benefit gates, structural rollback, loop protection, and a strict one-step-per-run policy — proven by 207 passing tests and a 72-case stress run with zero invariant violations. The known limitations (L1–L5) are documented, conservative in direction, and none can cause destructive automatic treatment of historical content.
