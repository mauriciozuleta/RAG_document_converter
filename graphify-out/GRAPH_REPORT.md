# Graph Report - PDF to RAG  (2026-10-06)

## Corpus Check
- 11 files · ~30,906 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 166 nodes · 295 edges · 14 communities (11 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3c0dc191`
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
- [[_COMMUNITY_Community 17|Community 17]]

## God Nodes (most connected - your core abstractions)
1. `App` - 32 edges
2. `process_pdf()` - 21 edges
3. `str` - 18 edges
4. `clean_text()` - 11 edges
5. `detect_chapter_number()` - 11 edges
6. `extract_hts()` - 10 edges
7. `detect_sections()` - 10 edges
8. `str` - 10 edges
9. `_is_heading()` - 9 edges
10. `build_markdown()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `is_hts()` --calls--> `extract_text()`  [INFERRED]
  hts_extract.py → pdf_to_rag.py
- `process_pdf()` --calls--> `is_hts()`  [EXTRACTED]
  pdf_to_rag.py → hts_extract.py
- `process_pdf()` --calls--> `extract_hts()`  [EXTRACTED]
  pdf_to_rag.py → hts_extract.py
- `main()` --calls--> `clean_text()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py
- `main()` --calls--> `detect_sections()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py

## Import Cycles
- None detected.

## Communities (14 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (31): ArgumentParser, main(), diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,, build_parser(), clean_text(), detect_sections(), extract_text(), _is_heading() (+23 more)

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
Cohesion: 0.25
Nodes (7): chapter, document_type, review_required, schema_version, sections, source, title

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (18): inspect_page(), Conservative, auditable extraction for arbitrary PDF layouts.  Source text and c, walk(), extract_hts(), is_hts(), _lines(), Coordinate-preserving HTS extraction using the existing pdfminer dependency., Return page-sized sections with explicit chapter and source metadata.      page_ (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (7): Commit messages, Dependencies, Developer OS integration, Graphify, Project Instructions, Project wiki, Tests

### Community 8 - "Community 8"
Cohesion: 0.29
Nodes (3): _clean_dnd_path(), str, Parse the path string returned by tkinterdnd2 (handles spaces & braces).

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (5): Harmonized Tariff Schedule of the United States, page-911 LIVE ANIMALS — PDF page 911, page-912 LIVE ANIMALS — PDF page 912, page-913 LIVE ANIMALS — PDF page 913, page-920 LIVE ANIMALS — PDF page 920

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (19): extract_document(), build_markdown(), process_pdf(), Render the RAG JSON structure as a Markdown document., Write the RAG data as a Markdown document to *output_path*., Write the RAG data as a Markdown document to *output_path*., Validate the built JSON structure.     Returns a (possibly empty) list of warni, Validate the built JSON structure.     Returns a (possibly empty) list of warni (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (5): chapter, document_type, sections, source, title

## Knowledge Gaps
- **25 isolated node(s):** `ArgumentParser`, `Widget`, `Button`, `document_type`, `chapter` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 8`, `Community 9`, `Community 17`?**
  _High betweenness centrality (0.304) - this node is a cross-community bridge._
- **Why does `process_pdf()` connect `Community 11` to `Community 0`, `Community 8`, `Community 2`, `Community 6`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Why does `extract_hts()` connect `Community 6` to `Community 0`, `Community 11`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **What connects `diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,`, `Conservative, auditable extraction for arbitrary PDF layouts.  Source text and c`, `Coordinate-preserving HTS extraction using the existing pdfminer dependency.` to the rest of the system?**
  _69 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.13068181818181818 - nodes in this community are weakly interconnected._
- **Should `Community 6` be split into smaller, more focused modules?**
  _Cohesion score 0.1076923076923077 - nodes in this community are weakly interconnected._
- **Should `Community 11` be split into smaller, more focused modules?**
  _Cohesion score 0.12987012987012986 - nodes in this community are weakly interconnected._