"""Verified native-grid export for the supplied ALADI/Caricom PDF layout."""
import bisect
import csv
import json
from collections import Counter
from pathlib import Path
import sys
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTLine, LTRect, LTTextLine
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from document_extract import walk

SOURCE = Path(r'C:\Users\donre\Downloads\tlc-caricom-colombia.pdf')
OUT = Path(__file__).parent / 'caricom-csv'
HEADERS = ['Item', 'Año', 'Descripción', 'Acuerdo', 'Otorgante', 'Copartícipes', 'Porcentual Ad-valorem', 'Residual Ad-valorem', 'Observaciones', 'Observaciones de Cronograma', 'Columna sin encabezado']

def cluster(values):
    groups = []
    for value in sorted(values):
        if not groups or value - groups[-1][-1] > 1:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [sum(group) / len(group) for group in groups]

def cell_text(chars):
    lines = []
    for char in sorted(chars, key=lambda c: (-round(c.y0, 1), c.x0)):
        if not lines or abs(char.y0 - lines[-1][0].y0) > 1:
            lines.append([char])
        else:
            lines[-1].append(char)
    return '\n'.join(''.join(c.get_text() for c in sorted(line, key=lambda c:c.x0)).strip() for line in lines).strip()

def main():
    OUT.mkdir(exist_ok=True)
    all_rows, report = [], []
    for number, page in enumerate(extract_pages(str(SOURCE)), 1):
        objects = list(walk(page))
        rules = [o for o in objects if isinstance(o, (LTLine,LTRect))]
        # The repeated ALADI body grid has continuous vertical rules.
        vertical = [o for o in rules if o.width < 1 and o.height > 100 and o.y1 < 510]
        xs = cluster([(o.x0+o.x1)/2 for o in vertical] + [742.7])
        if len(xs) != 12:
            raise ValueError(f'Page {number}: unexpected column grid {xs}')
        top = max(o.y1 for o in vertical)
        bottom = min(o.y0 for o in vertical)
        ys = cluster([top,bottom] + [(o.y0+o.y1)/2 for o in rules if o.height < 1 and o.width > 725 and bottom-1 <= o.y0 <= top+1])
        cells = [[[] for _ in range(11)] for _ in range(len(ys)-1)]
        assigned=[]
        for char in (o for o in objects if isinstance(o,LTChar)):
            x,y=(char.x0+char.x1)/2,(char.y0+char.y1)/2
            if xs[0] < x < xs[-1] and ys[0] < y < ys[-1]:
                c=bisect.bisect_right(xs,x)-1
                r=len(ys)-2-(bisect.bisect_right(ys,y)-1)
                cells[r][c].append(char)
                assigned.append(char.get_text())
        rows = [[cell_text(cell) for cell in row] for row in cells]
        rows = [row for row in rows if any(row)]
        source_codes = [o.get_text().strip() for o in objects if isinstance(o,LTTextLine) and 16<o.x0<20 and o.get_text().strip().isdigit() and bottom < o.y0 < top]
        assert [r[0] for r in rows if r[0]] == source_codes, f'Item sequence mismatch, page {number}'
        assert Counter(''.join(assigned).replace(' ','').replace('\n','')) == Counter(''.join(''.join(row) for row in rows).replace(' ','').replace('\n','')), f'Character loss, page {number}'
        path=OUT/f'page-{number:03d}.csv'
        with path.open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(HEADERS);writer.writerows(rows)
        all_rows.extend([[number,i,*row] for i,row in enumerate(rows,1)])
        report.append({'page':number,'rows':len(rows),'item_codes':len(source_codes),'characters':len(assigned)})
        print(f'Page {number}: {len(rows)} rows, item sequence and text verified',flush=True)
    with (OUT/'tlc-caricom-colombia.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['Página PDF','Fila en página',*HEADERS]);writer.writerows(all_rows)
    (OUT/'validation.json').write_text(json.dumps({'source':str(SOURCE),'pages':report,'total_rows':len(all_rows)},indent=2),encoding='utf-8')
    print('TOTAL',len(all_rows),flush=True)
if __name__=='__main__':main()
