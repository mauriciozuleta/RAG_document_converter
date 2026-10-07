import csv
from pathlib import Path
import tempfile
import unittest

from table_export import export_tables


class TableExportTests(unittest.TestCase):
    def test_exports_keep_identifiers_and_merges(self):
        data = {'sections': [{'source_page': 3, 'ocr_markdown': '<table><tr><th colspan="2">Header</th></tr><tr><td rowspan="2">0012</td><td>=1+2</td></tr><tr><td>A &amp; B<br>next</td></tr></table>'}]}
        with tempfile.TemporaryDirectory() as folder:
            paths = export_tables(data, folder, 'sample', 'csv')
            with open(paths[0], encoding='utf-8-sig', newline='') as stream:
                self.assertEqual(list(csv.reader(stream)), [['Header', ''], ['0012', '=1+2'], ['', 'A & B\nnext']])
            self.assertIn('page-3-table-1', paths[0])
            paths = export_tables(data, folder, 'sample', 'xlsx')
            from openpyxl import load_workbook
            workbook = load_workbook(paths[0])
            sheet = workbook['page-3-table-1']
            self.assertEqual(sheet['A2'].value, '0012')
            self.assertEqual(sheet['B2'].data_type, 's')
            self.assertEqual(str(sheet.merged_cells), 'A1:B1 A2:A3')
            workbook.close()

    def test_no_tables_does_not_write_empty_export(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'No structured tables'):
                export_tables({'sections': [{'source_page': 1, 'ocr_markdown': 'Text only'}]}, folder, 'empty', 'csv')
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_multiple_tables_and_pages(self):
        html = '<table><tr><td>value</td></tr></table>'
        with tempfile.TemporaryDirectory() as folder:
            paths = export_tables({'sections': [{'source_page': 2, 'ocr_markdown': html * 2}, {'source_page': 5, 'ocr_markdown': html}]}, folder, 'tables', 'csv')
            self.assertEqual(len(paths), 3)
            self.assertEqual(len(set(paths)), 3)
