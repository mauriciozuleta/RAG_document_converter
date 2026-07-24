"""
diagnose.py  —  Full pipeline diagnostic for pdf_to_rag.
Shows raw extraction, cleaned text, and exactly which headings are detected.

Usage:
    python diagnose.py "path/to/file.pdf"
"""
import sys
from pathlib import Path

# Import pipeline steps from the main module
sys.path.insert(0, str(Path(__file__).parent))
from pdf_to_rag import extract_text, clean_text, detect_sections, _is_heading

SEP = "=" * 70

def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose.py path/to/file.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"PDF: {pdf_path}")

    # ── 1. Raw extraction ──────────────────────────────────────────────
    print(f"\n{SEP}\n1. RAW EXTRACTION\n{SEP}")
    raw = extract_text(pdf_path)
    raw_lines = raw.splitlines()
    print(f"Lines: {len(raw_lines)}   Chars: {len(raw)}")
    print("\nFirst 30 lines:")
    for i, ln in enumerate(raw_lines[:30]):
        tag = "[BLANK]" if not ln.strip() else repr(ln)
        print(f"  {i:4d}  {tag}")

    # ── 2. Line-frequency table (what will be removed as headers) ──────
    print(f"\n{SEP}\n2. REPEATED-LINE CANDIDATES (count >= 3, len < 120)\n{SEP}")
    from collections import Counter
    freq = Counter(ln.strip() for ln in raw_lines if ln.strip())
    for text, count in freq.most_common(20):
        if count >= 3 and len(text) < 120:
            print(f"  {count:4d}x  {text!r}")

    # ── 3. Cleaned text ────────────────────────────────────────────────
    print(f"\n{SEP}\n3. CLEANED TEXT\n{SEP}")
    cleaned = clean_text(raw)
    clean_lines = cleaned.splitlines()
    print(f"Lines: {len(clean_lines)}   Chars: {len(cleaned)}")
    print("\nFirst 40 lines of cleaned text:")
    for i, ln in enumerate(clean_lines[:40]):
        tag = "[BLANK]" if not ln.strip() else repr(ln)
        print(f"  {i:4d}  {tag}")

    # ── 4. Heading detection on cleaned text ───────────────────────────
    print(f"\n{SEP}\n4. HEADING DETECTION ON CLEANED TEXT\n{SEP}")
    n = len(clean_lines)
    detected = []
    for i, line in enumerate(clean_lines):
        s = line.strip()
        if not s:
            continue
        passes_heading = _is_heading(line)
        prev_blank = (i == 0) or (clean_lines[i - 1].strip() == "")
        if passes_heading:
            marker = "✓ HEADING" if prev_blank else "✗ no-prev-blank"
            if prev_blank:
                detected.append((i, s))
            print(f"  Line {i:5d} | {marker:18s} | {s!r}")

    # ── 5. Sections summary ────────────────────────────────────────────
    print(f"\n{SEP}\n5. DETECTED SECTIONS\n{SEP}")
    sections = detect_sections(cleaned)
    print(f"Total sections (including chapter title): {len(sections)}")
    for j, sec in enumerate(sections):
        label = "CHAPTER TITLE" if j == 0 else f"Section {j}"
        print(f"  [{label}]  title={sec['title']!r}  content_chars={len(sec['content'])}")

if __name__ == "__main__":
    main()
