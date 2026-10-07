"""Conservative native extraction of continuous ruled PDF table bodies."""
from bisect import bisect_right
from collections import defaultdict
from pdfminer.layout import LTChar, LTLine, LTRect
from document_extract import walk


def cluster(values, tolerance=1):
    groups = []
    for value in sorted(values):
        if not groups or value - groups[-1][-1] > tolerance:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [sum(g) / len(g) for g in groups]


def cell_text(chars):
    lines = []
    for char in sorted(chars, key=lambda c: (-round(c.y0, 1), c.x0)):
        if not lines or abs(char.y0 - lines[-1][0].y0) > 1:
            lines.append([char])
        else:
            lines[-1].append(char)
    return '\n'.join(''.join(c.get_text() for c in sorted(line, key=lambda c:c.x0)).strip() for line in lines).strip()


def extract_grids(page):
    objects = list(walk(page))
    chars = [o for o in objects if isinstance(o, LTChar)]
    rules = [o for o in objects if isinstance(o, (LTLine, LTRect))]
    vertical = [o for o in rules if o.width <= 1 and o.height >= 20]
    horizontal = [o for o in rules if o.height <= 1 and o.width >= 20]
    groups = defaultdict(list)
    for line in vertical:
        groups[(round(line.y0), round(line.y1))].append(line)
    candidates = []
    for (bottom, top), lines in groups.items():
        xs = cluster([(o.x0+o.x1)/2 for o in lines])
        if len(xs) < 3:
            continue
        # Include outer borders that extend above a table body into its header.
        covering = cluster([(o.x0+o.x1)/2 for o in vertical if o.y0 <= bottom+1 and o.y1 >= top-1])
        left = [x for x in covering if x < xs[0]-1]
        right = [x for x in covering if x > xs[-1]+1]
        if left:
            xs.insert(0, max(left))
        if right:
            xs.append(min(right))
        full = [o for o in horizontal if o.x0 <= xs[0]+1 and o.x1 >= xs[-1]-1 and bottom-1 <= o.y0 <= top+1]
        ys = cluster([float(bottom), float(top)] + [(o.y0+o.y1)/2 for o in full])
        if len(ys) < 3:
            continue
        candidates.append((xs, ys))
    tables, used = [], set()
    for xs, ys in sorted(candidates, key=lambda t: -(t[0][-1]-t[0][0])*(t[1][-1]-t[1][0])):
        cells = [[[] for _ in range(len(xs)-1)] for _ in range(len(ys)-1)]
        selected = set()
        for index, char in enumerate(chars):
            x,y=(char.x0+char.x1)/2,(char.y0+char.y1)/2
            if xs[0] < x < xs[-1] and ys[0] < y < ys[-1]:
                selected.add(index)
                r=len(ys)-2-(bisect_right(ys,y)-1)
                cells[r][bisect_right(xs,x)-1].append(char)
        if not selected or selected & used:
            continue
        rows = [[cell_text(cell) for cell in row] for row in cells]
        rows = [row for row in rows if any(row)]
        if len(rows) < 2:
            continue
        used.update(selected)
        tables.append({'rows': rows, 'merges': [], 'bbox': [xs[0],ys[0],xs[-1],ys[-1]],
                       'note': 'Native ruled table body; separate/merged headers and content outside this grid require review.'})
    tables.sort(key=lambda t: (-t['bbox'][3],t['bbox'][0]))
    return tables, ''.join(c.get_text() for c in chars)
