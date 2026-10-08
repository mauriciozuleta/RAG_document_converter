"""Readable export and evidence-based warnings; never repair guessed wording."""
import re
from table_export import TableParser


def readable_markdown(text):
    def table(match):
        html = match.group(0)
        parser = TableParser()
        try:
            parser.feed(html)
        except ValueError:
            return html
        if len(parser.tables) != 1 or parser.tables[0][1]:
            # Markdown cannot represent merged cells faithfully.
            return re.sub(r'(</tr>)', r'\1\n', html)
        grid, _ = parser.tables[0]
        def row(cells):
            return '| ' + ' | '.join(c.replace('|', '\\|').replace('\n', '<br>') for c in cells) + ' |'
        # Do not mislabel the first data row as a header.
        return '\n' + '\n'.join([row([f'Column {n+1}' for n in range(len(grid[0]))]),
                                  row(['---'] * len(grid[0]))] + [row(r) for r in grid]) + '\n'
    text = re.sub(r'<table\b[^>]*>.*?</table>', table, text, flags=re.I | re.S)
    return re.sub(r'</?(?:html|body|div)\b[^>]*>', '', text, flags=re.I).strip()


def quality_warnings(raw, markdown):
    res = raw.get('res', raw)
    scores = res.get('overall_ocr_res', {}).get('rec_scores', [])
    warnings = []
    if '<table' in markdown.lower():
        warnings.append('Verify table identifiers, units, superscripts and merged cells against the source.')
    if scores and any(float(s) < .90 for s in scores):
        warnings.append('Some recognized lines have confidence below 0.90; compare with source.')
    if re.search(r'[A-Za-z]{28,}', markdown):
        warnings.append('Unusually long joined words suggest missing spaces or recognition errors.')
    if markdown.count('$') % 2 or re.search(r'\^\{\$', markdown):
        warnings.append('Malformed mathematical notation; verify symbols and superscripts.')
    return warnings
