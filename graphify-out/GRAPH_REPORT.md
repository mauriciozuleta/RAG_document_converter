# Graph Report - PDF to RAG  (2026-10-06)

## Corpus Check
- 11 files · ~12,099 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 170 nodes · 317 edges · 17 communities (11 shown, 6 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `58cfe634`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 17|Community 17]]

## God Nodes (most connected - your core abstractions)
1. `App` - 32 edges
2. `process_pdf()` - 24 edges
3. `str` - 18 edges
4. `detect_chapter_number()` - 12 edges
5. `clean_text()` - 11 edges
6. `extract_hts()` - 10 edges
7. `detect_sections()` - 10 edges
8. `build_markdown()` - 10 edges
9. `str` - 10 edges
10. `extract_document()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `extract_hts()` --calls--> `inspect_page()`  [EXTRACTED]
  hts_extract.py → document_extract.py
- `process_pdf()` --calls--> `extract_document()`  [EXTRACTED]
  pdf_to_rag.py → document_extract.py
- `is_hts()` --calls--> `extract_text()`  [INFERRED]
  hts_extract.py → pdf_to_rag.py
- `process_pdf()` --calls--> `is_hts()`  [EXTRACTED]
  pdf_to_rag.py → hts_extract.py
- `process_pdf()` --calls--> `extract_hts()`  [EXTRACTED]
  pdf_to_rag.py → hts_extract.py

## Import Cycles
- None detected.

## Communities (17 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.14
Nodes (29): main(), diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,, is_hts(), clean_text(), detect_sections(), extract_text(), _is_heading(), _join_wrapped_lines() (+21 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (8): _enable_high_dpi(), _hide_console_window(), pdf_to_rag_ui.py ---------------- Simple GUI for the PDF → RAG pipeline. Drag, Redirect stdout/stderr to a tkinter ScrolledText widget., Enable crisp rendering on Windows high-DPI displays., Hide the extra console window on Windows for this GUI app., _TextRedirect, ScrolledText

### Community 4 - "Community 4"
Cohesion: 0.29
Nodes (4): Button, int, str, Widget

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (22): ArgumentParser, build_json(), build_parser(), detect_chapter_number(), main(), process_pdf(), int, Assemble the final RAG JSON object.      Schema:     {         "chapter": <i (+14 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (6): extract_hts(), _lines(), Coordinate-preserving HTS extraction using the existing pdfminer dependency., Return page-sized sections with explicit chapter and source metadata.      page_, Return page-sized sections with explicit chapter and source metadata.      pag, PreservationTests

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (7): Commit messages, Dependencies, Developer OS integration, Graphify, Project Instructions, Project wiki, Tests

### Community 8 - "Community 8"
Cohesion: 0.33
Nodes (3): _clean_dnd_path(), bool, Parse the path string returned by tkinterdnd2 (handles spaces & braces).

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (5): Harmonized Tariff Schedule of the United States, page-911 LIVE ANIMALS — PDF page 911, page-912 LIVE ANIMALS — PDF page 912, page-913 LIVE ANIMALS — PDF page 913, page-920 LIVE ANIMALS — PDF page 920

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (15): extract_document(), inspect_page(), Conservative, auditable extraction for arbitrary PDF layouts.  Source text and c, walk(), create_pipeline(), enrich_document(), parse_pages(), Local PaddleOCR PP-StructureV3 enrichment, retaining native PDF evidence. (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.40
Nodes (5): Write the RAG data as a Markdown document to *output_path*., Write the RAG data as a Markdown document to *output_path*., Write the RAG data as a Markdown document to *output_path*., Write the RAG data as a Markdown document to *output_path*., save_markdown()

## Knowledge Gaps
- **13 isolated node(s):** `ArgumentParser`, `Widget`, `Button`, `Graphify`, `Project wiki` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 8`, `Community 9`, `Community 13`, `Community 14`, `Community 17`?**
  _High betweenness centrality (0.365) - this node is a cross-community bridge._
- **Why does `process_pdf()` connect `Community 5` to `Community 0`, `Community 2`, `Community 6`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.241) - this node is a cross-community bridge._
- **Why does `detect_chapter_number()` connect `Community 5` to `Community 0`, `Community 2`, `Community 6`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **What connects `diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,`, `Conservative, auditable extraction for arbitrary PDF layouts.  Source text and c`, `Coordinate-preserving HTS extraction using the existing pdfminer dependency.` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.14112903225806453 - nodes in this community are weakly interconnected._
- **Should `Community 5` be split into smaller, more focused modules?**
  _Cohesion score 0.09057971014492754 - nodes in this community are weakly interconnected._