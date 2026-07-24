# Graph Report - PDF to RAG  (2026-07-24)

## Corpus Check
- 3 files · ~5,505 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 99 nodes · 198 edges · 6 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]

## God Nodes (most connected - your core abstractions)
1. `App` - 32 edges
2. `str` - 18 edges
3. `process_pdf()` - 14 edges
4. `str` - 10 edges
5. `clean_text()` - 9 edges
6. `_is_heading()` - 8 edges
7. `_looks_table_row()` - 7 edges
8. `detect_sections()` - 7 edges
9. `detect_chapter_number()` - 7 edges
10. `_TextRedirect` - 7 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `clean_text()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py
- `main()` --calls--> `detect_sections()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py
- `main()` --calls--> `extract_text()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py
- `main()` --calls--> `_is_heading()`  [EXTRACTED]
  diagnose.py → pdf_to_rag.py

## Import Cycles
- None detected.

## Communities (6 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.19
Nodes (22): build_markdown(), clean_text(), _join_wrapped_lines(), _looks_image_artifact_line(), _looks_list_bullet(), _looks_table_row(), _looks_title_case(), _normalise_table_block() (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (6): App, PDF → RAG Converter GUI., Clear all user-input fields and reset output actions state., Animate a simple ASCII spinner while conversion is running., Open the output folder in the system file explorer., Copy the generated JSON file(s) to a user-chosen location.

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (15): ArgumentParser, build_json(), build_parser(), detect_chapter_number(), main(), process_pdf(), int, Assemble the final RAG JSON object.      Schema:     {         "chapter": <i (+7 more)

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (6): int, str, Redirect stdout/stderr to a tkinter ScrolledText widget., Create a scrollable host for the full UI (both axes)., _TextRedirect, ScrolledText

### Community 4 - "Community 4"
Cohesion: 0.24
Nodes (5): Button, _clean_dnd_path(), bool, Parse the path string returned by tkinterdnd2 (handles spaces & braces)., Widget

### Community 5 - "Community 5"
Cohesion: 0.33
Nodes (8): main(), diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,, detect_sections(), extract_text(), _is_heading(), Extract raw text from a PDF using pdfminer.six (deterministic, no AI)., Return True when a line qualifies as a section heading.     ALL conditions must, Split cleaned text into sections using a three-pass heading pipeline.      Pas

## Knowledge Gaps
- **3 isolated node(s):** `ArgumentParser`, `Widget`, `Button`
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.566) - this node is a cross-community bridge._
- **Why does `process_pdf()` connect `Community 2` to `Community 0`, `Community 5`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Why does `_TextRedirect` connect `Community 3` to `Community 2`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **What connects `diagnose.py  —  Full pipeline diagnostic for pdf_to_rag. Shows raw extraction,`, `ArgumentParser`, `pdf_to_rag.py ------------- Converts FAA handbook PDF files into structured JS` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.13970588235294118 - nodes in this community are weakly interconnected._