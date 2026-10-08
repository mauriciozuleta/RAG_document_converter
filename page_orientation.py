"""Normalize dominant native-text orientation before layout grouping."""
from collections import Counter
import math
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import LTChar, LAParams


def characters(obj):
    if isinstance(obj, LTChar):
        yield obj
    elif hasattr(obj, '__iter__'):
        for child in obj:
            yield from characters(child)


def correction(layout):
    votes = Counter()
    for char in characters(layout):
        if not char.get_text().strip():
            continue
        a,b = char.matrix[:2]
        angle = math.degrees(math.atan2(b,a)) % 360
        quadrant = (round(angle / 90) * 90) % 360
        if abs((angle - quadrant + 180) % 360 - 180) <= 8:
            votes[quadrant] += 1
    if not votes:
        return 0
    angle, count = votes.most_common(1)[0]
    return angle if count >= 20 and count / sum(votes.values()) >= .8 else 0


def extract_pages(path, page_numbers=None, laparams=None):
    manager = PDFResourceManager()
    device = PDFPageAggregator(manager, laparams=laparams or LAParams(detect_vertical=True, all_texts=True))
    interpreter = PDFPageInterpreter(manager, device)
    try:
        with open(path, 'rb') as stream:
            for page in PDFPage.get_pages(stream, pagenos=page_numbers):
                interpreter.process_page(page)
                layout = device.get_result()
                angle = correction(layout)
                original = page.rotate
                if angle:
                    try:
                        page.rotate = (original + angle) % 360
                        interpreter.process_page(page)
                        layout = device.get_result()
                    finally:
                        page.rotate = original
                layout.orientation_correction = angle
                yield layout
    finally:
        device.close()
