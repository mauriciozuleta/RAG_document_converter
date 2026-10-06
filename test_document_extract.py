"""Small real PDF fixtures generated without additional dependencies."""
import tempfile
import unittest
from pathlib import Path

from document_extract import extract_document
from pdf_to_rag import build_markdown, process_pdf


def write_pdf(path, stream):
    stream = stream.encode('ascii')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    data = b'%PDF-1.4\n'
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(index).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
    xref = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    data += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    data += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    path.write_bytes(data)


class DocumentTests(unittest.TestCase):
    def test_columns_repetition_and_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'general.pdf'
            stream = '\n'.join(f'BT /F1 12 Tf {x} {y} Td ({text}) Tj ET'
                               for x, y, text in [(40, 700, 'Left column'), (330, 700, 'Right column'),
                                                  (40, 680, '0101'), (330, 680, 'Free'),
                                                  (40, 660, 'Free'), (40, 640, 'Free'),
                                                  (40, 600, 'Figure 1. Keep this caption'),
                                                  (40, 580, '``` literal fence')])
            write_pdf(path, stream)
            data = extract_document(path)
            page = data['sections'][0]
            self.assertEqual(page['source_page'], 1)
            self.assertEqual(page['raw_text'].count('Free'), 3)
            self.assertEqual(len(page['source_lines']), 8)
            self.assertTrue(all(len(line['bbox']) == 4 for line in page['source_lines']))
            self.assertIn('Figure 1. Keep this caption', page['content'])
            visual = page['layout_text'].splitlines()[0]
            self.assertLess(visual.index('Left column'), visual.index('Right column'))
            fenced = {'sections': [{'id': '1', 'title': 'Literal', 'content': '```'}]}
            self.assertIn('````text', build_markdown(fenced))
            outputs = process_pdf(str(path), folder, output_format='both')
            self.assertEqual(len(outputs), 2)

    def test_unextractable_page_is_not_silently_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'vector.pdf'
            write_pdf(path, '40 40 300 400 re S')
            data = extract_document(path)
            self.assertTrue(data['review_required'])
            self.assertIn('No extractable text', data['sections'][0]['warnings'][0])
            self.assertIn('Extraction review:', build_markdown(data))


if __name__ == '__main__':
    unittest.main()
