# Graph Report - PDF to RAG  (2026-10-05)

## Corpus Check
- 7 files · ~15,084 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 135 nodes · 248 edges · 18 communities (15 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9251ac58`
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
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]

## God Nodes (most connected - your core abstractions)
1. `App` - 32 edges
2. `str` - 18 edges
3. `process_pdf()` - 17 edges
4. `clean_text()` - 11 edges
5. `detect_sections()` - 10 edges
6. `detect_chapter_number()` - 10 edges
7. `str` - 10 edges
8. `_is_heading()` - 9 edges
9. `extract_hts()` - 7 edges
10. `extract_text()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `clean_text()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py
- `main()` --calls--> `extract_text()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py
- `is_hts()` --calls--> `extract_text()`  [INFERRED]
  hts_extract.py → pdf_to_rag.py
- `process_pdf()` --calls--> `extract_hts()`  [EXTRACTED]
  pdf_to_rag.py → hts_extract.py
- `main()` --calls--> `detect_sections()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py

## Import Cycles
- None detected.

## Communities (18 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.40
Nodes (11): clean_text(), _join_wrapped_lines(), _looks_image_artifact_line(), _looks_list_bullet(), _looks_table_row(), _normalise_table_block(), bool, str (+3 more)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (4): App, PDF → RAG Converter GUI., Animate a simple ASCII spinner while conversion is running., Open the output folder in the system file explorer.

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (8): _enable_high_dpi(), _hide_console_window(), pdf_to_rag_ui.py ---------------- Simple GUI for the PDF → RAG pipeline. Drag, Redirect stdout/stderr to a tkinter ScrolledText widget., Enable crisp rendering on Windows high-DPI displays., Hide the extra console window on Windows for this GUI app., _TextRedirect, ScrolledText

### Community 4 - "Community 4"
Cohesion: 0.43
Nodes (3): Button, bool, Widget

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (8): main(), diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,, detect_sections(), _is_heading(), Return True when a line qualifies as a section heading.     ALL conditions must, Return True when a line qualifies as a section heading.     ALL conditions must, Split cleaned text into sections using a three-pass heading pipeline.      Pas, Split cleaned text into sections using a three-pass heading pipeline.      Pas

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (12): extract_hts(), _lines(), Coordinate-preserving HTS extraction using the existing pdfminer dependency.  Ta, Return page-sized sections with explicit chapter and source metadata.      page_, build_json(), detect_chapter_number(), int, Assemble the final RAG JSON object.      Schema:     {         "chapter": <i (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (7): Commit messages, Dependencies, Developer OS integration, Graphify, Project Instructions, Project wiki, Tests

### Community 8 - "Community 8"
Cohesion: 0.29
Nodes (3): _clean_dnd_path(), str, Parse the path string returned by tkinterdnd2 (handles spaces & braces).

### Community 10 - "Community 10"
Cohesion: 0.40
Nodes (6): is_hts(), extract_text(), process_pdf(), Extract raw text from a PDF using pdfminer.six (deterministic, no AI)., Run the full pipeline for a single PDF:       extract → clean → detect sections, Run the full pipeline for a single PDF:       extract → clean → detect sections

### Community 11 - "Community 11"
Cohesion: 0.33
Nodes (6): build_markdown(), Render the RAG JSON structure as a Markdown document., Write the RAG data as a Markdown document to *output_path*., Render the RAG JSON structure as a Markdown document., Write the RAG data as a Markdown document to *output_path*., save_markdown()

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (5): chapter, document_type, sections, source, title

### Community 13 - "Community 13"
Cohesion: 0.50
Nodes (4): ArgumentParser, build_parser(), main(), pdf_to_rag.py ------------- Converts PDF files, including HTS schedules, into

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (3): _looks_title_case(), Lenient Title Case check.     The first word must be capitalised; every subsequ, Lenient Title Case check.     The first word must be capitalised; every subsequ

### Community 15 - "Community 15"
Cohesion: 0.67
Nodes (3): Write the JSON structure to *output_path* with UTF-8 encoding., Write the JSON structure to *output_path* with UTF-8 encoding., save_json()

### Community 16 - "Community 16"
Cohesion: 0.67
Nodes (3): Validate the built JSON structure.     Returns a (possibly empty) list of warni, Validate the built JSON structure.     Returns a (possibly empty) list of warni, validate()

## Knowledge Gaps
- **14 isolated node(s):** `ArgumentParser`, `Widget`, `Button`, `document_type`, `chapter` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 8`, `Community 9`, `Community 17`?**
  _High betweenness centrality (0.393) - this node is a cross-community bridge._
- **Why does `process_pdf()` connect `Community 10` to `Community 0`, `Community 2`, `Community 5`, `Community 6`, `Community 8`, `Community 11`, `Community 13`, `Community 15`, `Community 16`?**
  _High betweenness centrality (0.175) - this node is a cross-community bridge._
- **Why does `detect_chapter_number()` connect `Community 6` to `Community 0`, `Community 2`, `Community 8`, `Community 10`, `Community 13`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **What connects `diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,`, `Coordinate-preserving HTS extraction using the existing pdfminer dependency.  Ta`, `Return page-sized sections with explicit chapter and source metadata.      page_` to the rest of the system?**
  _51 weakly-connected nodes found - possible documentation gaps or missing edges._