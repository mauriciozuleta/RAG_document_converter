# OCR accuracy review - 2026-10-08

Tested source PDF pages 2, 4 and 596, each freshly rendered at 180 and 300 DPI. Compared original multilingual server recognition, English PP-OCRv5, English PP-OCRv4, and two detector settings. Detailed raw JSON/Markdown and timing logs are retained locally in verification/accuracy.

Selected: English PP-OCRv5 mobile recognition, server detection, 300 DPI crops, detection thresholds 0.2/0.3 and expansion ratio 1.2. Kept headers/footnotes rather than allowing the layout Markdown exporter to omit them. English is the new default; multilingual recognition remains selectable through PDF_RAG_OCR_MODEL.

Observed improvements:
- Page 4's chapter-4 description matches the reference wording and punctuation in the selected trial; the old output was heavily joined/corrupted.
- Page 596 paragraph 4(a) now includes the previously missing first line. Paragraphs 1(b), 2(b) and 4(b) are also present.
- Page 2 keeps N and No. in separate rows and identifies cm2/cm3 separately. Degree recognition improved to 360 degrees with its symbol in the final export.

Remaining limitations:
- Superscript styling is lost in cm2/cm3/m2/m3; Celsius and litre symbols still contain recognition errors.
- Page 596 retains some e/c substitutions and list-marker errors. Confidence values alone do not identify all mistakes.
- These observations are targeted spot checks, not a whole-document accuracy score. No guessed spelling/symbol replacements are applied.

Runtime: Paddle 3.3.1 cu126 Windows reports cuDNN 9.9.0 but pins the 9.5.1.17 package. Installed nvidia-cudnn-cu12 9.9.0.52 in the isolated GPU environment and verified GPU convolution and OCR without the mismatch warning. Bootstrap applies this targeted override for builds reporting 9.9. It deliberately overrides inconsistent wheel metadata: pip check will report that one known dependency conflict.

Deliverables: Downloads/OCR_accuracy_review/review-pages-2-4-596.md and .json. A broader first-50-page run is also generated there. All OCR remains explicitly unverified.

## Broader run and startup validation

The initial three-worker 50-page trial suffered an abrupt process-pool termination after 15 recovered regions; the log did not establish its root cause. A two-worker retry reused successful checkpoints and recovered all 49 flagged regions across the first 50 pages, preserving page order. This verifies completion/text presence, not whole-document accuracy. Keep two workers for this document pending further three-worker stability testing.

54 unit tests pass (two external-fixture tests skipped). Normal launch no longer runs OCR benchmarks or preloads models, and the warmed local launcher returned in under a second. Full benchmark/model preparation is explicitly requested with -Rebenchmark. First conversion still loads models. Model/dependency installation remains a first-use cost.
