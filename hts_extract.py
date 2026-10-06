"""Coordinate-preserving HTS extraction using the existing pdfminer dependency.

Table rows are physical PDF lines, not inferred tariff records. Blank cells
remain blank; wrapped descriptions and rates retain their column positions.
"""
import re
from pathlib import Path

from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextLine, LTLine, LTRect, LAParams
from document_extract import inspect_page


def is_hts(path):
    text = extract_text(path, maxpages=5)
    return bool(re.search(r"Harmonized\s+Tariff\s+Schedule", text, re.I))


def _lines(obj):
    if isinstance(obj, LTTextLine):
        yield obj
    elif hasattr(obj, "__iter__"):
        for child in obj:
            yield from _lines(child)


def extract_hts(path, page_numbers=None):
    """Return page-sized sections with explicit chapter and source metadata.

    page_numbers is zero-based and intended for focused verification.
    """
    selected = sorted(set(page_numbers)) if page_numbers is not None else None
    result = {"document_type": "hts", "chapter": None,
              "title": "Harmonized Tariff Schedule of the United States",
              "source": Path(path).name, "sections": []}
    chapter = None
    chapter_title = "Front matter and general notes"
    for index, page in enumerate(extract_pages(path, page_numbers=selected, laparams=LAParams(detect_vertical=True, all_texts=True))):
        number = selected[index] + 1 if selected is not None else index + 1
        details = inspect_page(page)
        lines = sorted(_lines(page), key=lambda line: (-line.y0, line.x0))
        # A requested page subset may begin after the chapter's title page.
        for line in lines:
            marker = re.fullmatch(r'(\d{1,2})-\d+', line.get_text().strip())
            if marker and line.y0 > page.height * .85:
                number_from_margin = int(marker.group(1))
                if chapter != number_from_margin:
                    chapter = number_from_margin
                    chapter_title = f'Chapter {chapter}'
                break
        # Only centered, standalone chapter headings qualify; origin rules in
        # general notes also contain left-aligned "Chapter N" labels.
        for line in lines:
            match = re.fullmatch(r"CHAPTER\s+(\d{1,2})", line.get_text().strip())
            if match and abs((line.x0 + line.x1) / 2 - page.width / 2) < 50:
                chapter = int(match.group(1))
                below = [ln for ln in lines if 0 < line.y0 - ln.y0 < 45
                         and abs((ln.x0 + ln.x1) / 2 - page.width / 2) < 80]
                chapter_title = " ".join(ln.get_text().strip() for ln in below) or f"Chapter {chapter}"
                break

        # Long vertical rules provide actual column boundaries, not guessed
        # whitespace widths. Unsupported tables retain positional text below.
        edges = sorted({round((obj.x0 + obj.x1) / 2, 1) for obj in page
                        if isinstance(obj, (LTLine, LTRect))
                        and obj.height > page.height * .4 and obj.width <= 2})
        table = len(edges) == 8 and any("Article Description" in ln.get_text() for ln in lines)
        labels = ["Heading/Subheading", "Statistical suffix", "Article description",
                  "Unit of quantity", "General duty", "Special duty", "Column 2 duty"]
        rows = []
        for line in lines:
            text = line.get_text().strip()
            if not text:
                continue
            if rows and abs(rows[-1][0] - line.y0) <= 2:
                rows[-1][1].append(line)
            else:
                rows.append((line.y0, [line]))
        rendered = []
        table_rows = []
        header_bottom = min((ln.y0 for ln in lines if ln.get_text().strip() in {"General", "Special"}), default=0)
        for y, row in rows:
            row.sort(key=lambda ln: ln.x0)
            if table and y < header_bottom - 3 and all(edges[0] - 2 <= ln.x0 < edges[-1] for ln in row):
                cells = [""] * 7
                for line in row:
                    col = next((i for i in range(7) if edges[i] - 1 <= line.x0 < edges[i + 1] - 1), None)
                    if col is not None:
                        cells[col] = (cells[col] + " " + line.get_text().strip()).strip()
                table_rows.append(dict(zip(labels, cells)))
                rendered.append(" | ".join(f"{label}: {value}" for label, value in zip(labels, cells) if value))
            else:
                # Preserve horizontal spacing for other tables, headings, notes.
                output = ""
                for line in row:
                    column = max(0, round(line.x0 / 4))
                    output += " " * max(1 if output else 0, column - len(output)) + line.get_text().strip()
                rendered.append(output.rstrip())
        section = {"id": f"page-{number}", "title": f"{chapter_title} — PDF page {number}",
                   "chapter": chapter, "chapter_title": chapter_title,
                   "source_page": number, "content": "\n".join(rendered), "tags": []}
        section.update(details)
        section["content"] = details["layout_text"]
        if table_rows:
            section["table_rows"] = table_rows
            section["warnings"].append("Table rows are physical lines, not complete records; use source coordinates and layout for hierarchy and continuations.")
            section["table_row_semantics"] = "Physical lines; blank cells and continuations are not inferred."
        result["sections"].append(section)
        if number % 100 == 0:
            print(f"[INFO] Extracted PDF page {number}", flush=True)
    result["schema_version"] = 2
    result["review_required"] = any(s["warnings"] for s in result["sections"])
    return result
