## 2026-10-07 - Offer three GPU workers with measured memory limits

The user freed RAM and requested a third GPU worker option, with startup memory benchmarking to limit concurrency when resources are insufficient.

- Added three-worker support to the GPU benchmark, CLI and bounded scheduler; UI options depend on measured capacity and successful benchmarks.
- Record peak process RAM and CUDA reserved memory, and measure available RAM/VRAM afresh on every launch.
- Budget explicit growth/headroom and recheck availability before conversion; log worker reductions and reject starts when no worker fits.
- Added regression tests for independent RAM/VRAM limits, measured peaks and conversion-time changes.

## 2026-10-07 ? Automate hardware setup and default to two GPU workers

The user requested automatic dependency installation and CPU/GPU benchmarking at launch, with two GPU OCR workers and a CPU organizer instead of restrictive static limits.

- Added automatic Windows bootstrap, NVIDIA UUID selection, CUDA package selection, model preparation, cached startup benchmarks and visible failure handling.
- Defaulted to two GPU OCR workers; removed static RAM and single-GPU limits.
- Moved GPU crop preparation into a bounded CPU coordinator queue, preserving inline result ordering and caches.
- Added setup/worker regression coverage and verified real CPU, one-GPU and two-GPU benchmarks on RTX 3060.
- Updated launch and deployment documentation.

## 2026-10-07 ? Publish application to GitHub

The user requested publication to mauriciozuleta/RAG_document_converter.

- Connected origin and merged its initial README history without overwriting remote work.
- Included existing local worker isolation, cancellation, page-checkpoint code and regression tests.
- Added repository setup instructions; verified 34 tests (two external fixtures skipped).

## 2026-10-07 ? Prepare and verify a single-GPU OCR trial

The user approved the required GPU software installation and requested readiness for a trial while the CPU app was running.

- Installed an isolated CUDA 12.6/Paddle GPU environment; retained the current CPU environment and job.
- Added explicit GPU device selection, one-worker enforcement, separate caches and a GPU launcher.
- Added a trial command and telemetry report; verified CUDA computation, actual OCR recognition and both environments' tests.

## 2026-10-07 ? Bounded parallel CPU OCR

The user approved multiple OCR workers and asked whether GPU acceleration was possible.

- Added a GUI worker selector and CLI/API option, bounded two-process scheduling, persistent worker models and a memory/CPU fallback.
- Preserved ordered inline output, cache reuse, unresolved failures and parent-owned progress reporting.
- Checked hardware and verified process scheduling in tests; left the active conversion and CPU installation undisturbed.

## 2026-10-07 ? Show total and remaining OCR flags

The user requested a flagged-section count after native text conversion and progress such as 1 of 100.

- Added total flagged sections, global per-region ordinals and remaining counts to conversion logs.
- Kept unresolved flags distinct from completed checks and reported disabled-OCR pending counts.

## 2026-10-07 ? Two-pass flagged OCR with inline output

The user requested flags for missed image tables, native extraction before OCR, insertion at the original missing positions, and correct transitions across multipage image sections.

- Added ordered recovery flags, image-tile grouping, textless-vector-figure candidates and page-sequence tracking.
- Fixed Markdown omissions and integrated recovered text into JSON/Markdown and page-level CSV/Excel outputs.
- Preserved unresolved markers and successful region checkpoints for retry; added ordering, transitions and failure tests.

## 2026-10-07 ? Recover embedded images on mixed-content pages

The user reported that native-first conversion skipped images and requested automatic OCR of missing content.

- Enabled automatic OCR in the GUI and added image-region detection and cropped OCR while retaining native evidence.
- Preserved image-derived tables and non-table Markdown sidecars for spreadsheet exports.
- Invalidated old table checkpoints that omitted images; tested mixed-content rendering, outputs and resume.

## 2026-10-07 ? Remove forced OCR from large-document conversion

The user requested a practical update for roughly 1,000-page digital PDFs after forced OCR caused excessive runtimes.

- Added native-first ruled-table extraction, page-level optional OCR, and OCR-off GUI defaults.
- Added incremental CSV output, source-keyed page checkpoints, automatic resume, progress estimates and review reports.
- Verified all 94 CARICOM pages in about 11 seconds against the earlier 3,535-row export; tested cached reuse and extraction policy.

## 2026-10-07 ? Validate CARICOM PDF export

Tested the user-supplied PDF after a reported stalled conversion and exported CSV files.

- Added a reproducible document-specific native-grid export with per-page validation.
- Exported all 94 pages and checked 3,535 rows, identifiers, accents and cell text.
- Documented slow OCR initialization/recognition; no general app behavior changed.

## 2026-10-07 ? PDF table export

Requested a PDF-only table conversion option with CSV and Excel output.

- Added Tables CSV and Tables Excel options and corresponding CLI formats.
- Reused PaddleOCR table recognition, retaining page/table provenance and merged-cell structure.
- Added tests for CSV quoting, identifiers, literal formulas, merged cells, multiple tables, and no-table errors.

# Changelog

## 2026-10-06 - Isolate OCR from the GUI

The user reported a crash on a 351-page tariff PDF. The old app was still consuming CPU and marked not responding. Moved conversion into an isolated process and added recovery evidence without asserting an unproven library-level cause.

- Added cancellable subprocess conversion and durable crash logs.
- Saved detailed OCR data and Markdown checkpoints per page to reduce accumulated memory.
- Limited OCR to four CPU threads and kept controls accessible during conversion.
- Added worker success, failure, abrupt-exit, cancellation, and checkpoint tests.


## 2026-10-06 - Integrate local PaddleOCR

The user requested installation and integration of an open-source OCR option for another test. Added PaddleOCR PP-StructureV3 for local CPU OCR and table parsing while preserving native evidence.

- Added isolated environment requirements and GUI launcher.
- Added GUI OCR toggle, page selection, and CLI engine/page flags.
- Exported model Markdown, structured results, and image assets alongside native text.
- Added page-range and evidence-preservation tests.


## 2026-10-06 - General page-aware preservation

The user requested reliable conversion beyond HTS documents. The general pipeline now retains source text and page coordinates, reports extraction limitations, and preserves layout in Markdown. OCR remains a required follow-up for scans.

- Added general PDF layout extraction and per-page review warnings.
- Made spatial text authoritative for HTS; preserved indentation and superscripts.
- Added seven tests including real HTS checks and generated multi-column/empty-page fixtures.
- Preserved source Markdown with safe fenced output.


## 2026-10-05 ? Preserve HTS extraction data

The user requested fixes after comparing a damaged HTS JSON export with the original PDF. The converter now preserves meaningful text and uses page coordinates for HTS schedules.

- Removed destructive repeated-line and numeric cleaning.
- Retained preamble and title-section content; restricted filename chapter detection.
- Added automatic HTS routing, page provenance, chapter metadata, and physical table rows.
- Added regression tests and verified original Chapter 1 codes, suffixes, units, and duties.


## 2026-08-19 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-08-14 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

## 2026-07-24 — Initial analysis

Generated by Developer OS's project analysis pipeline (Coder model).

---

