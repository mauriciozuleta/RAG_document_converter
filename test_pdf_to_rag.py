import os
import unittest

from pdf_to_rag import clean_text, detect_sections, build_json, detect_chapter_number
from hts_extract import extract_hts


class PreservationTests(unittest.TestCase):
    def test_cleaning_keeps_meaningful_repetition_and_numbers(self):
        text = '0101\n10\n20\n00\nFree\nFree\nFree\nAdditional U.S. Notes\n(cid:42)'
        self.assertEqual(clean_text(text), text)

    def test_preamble_and_title_body_survive(self):
        text = 'Opening material.\n\nOverview\n\n' + 'Body text. ' * 30
        result = build_json(1, detect_sections(text))
        content = '\n'.join(s['content'] for s in result['sections'])
        self.assertIn('Opening material.', content)
        self.assertIn('Body text.', content)
        single = build_json(1, [{'title': 'Content', 'content': 'Entire body'}])
        self.assertEqual(single['sections'][0]['content'], 'Entire body')

    def test_year_is_not_a_chapter(self):
        for name in ['2026HTSRev20.pdf', '2026_hts.pdf']:
            self.assertEqual(detect_chapter_number(name), 0)
        for name in ['chapter_3.pdf', 'ch3.pdf', 'chapter3.pdf', '03.pdf']:
            self.assertEqual(detect_chapter_number(name), 3)

    @unittest.skipUnless(os.environ.get('HTS_TEST_PDF'), 'Set HTS_TEST_PDF to the 2026 Revision 20 PDF')
    def test_original_chapter_one(self):
        data = extract_hts(os.environ['HTS_TEST_PDF'], page_numbers=[910, 911, 912])
        notes, table, cattle = data['sections']
        self.assertEqual(notes['chapter'], 1)
        self.assertEqual(notes['chapter_title'], 'LIVE ANIMALS')
        self.assertIn('Additional U.S. Notes', notes['content'])
        rows = {r['Heading/Subheading']: r for r in table['table_rows'] if r['Heading/Subheading']}
        self.assertEqual(rows['0101.21.00']['General duty'], 'Free')
        self.assertEqual(rows['0101.30.00']['General duty'], '6.8%')
        self.assertEqual(rows['0101.30.00']['Column 2 duty'], '15%')
        self.assertEqual(rows['0101.30.00']['Statistical suffix'], '00')
        self.assertEqual(rows['0101.90.40']['General duty'], '4.5%')
        self.assertTrue(any(r['Statistical suffix'] == '10' and r['Unit of quantity'] == 'No.' for r in table['table_rows']))
        self.assertIn('P, PA, PE, S, SG)', table['content'])
        self.assertIn('6.6¢/kg', cattle['content'])
        for section in data['sections']:
            for line in section['source_lines']:
                self.assertIn(line['text'].strip(), section['layout_text'])
        dairy = next(line for line in table['layout_text'].splitlines() if 'Dairy:' in line)
        male = next(line for line in table['layout_text'].splitlines() if 'Male...' in line)
        self.assertGreater(male.index('Male'), dairy.index('Dairy'))

    @unittest.skipUnless(os.environ.get('HTS_TEST_PDF'), 'Set HTS_TEST_PDF for integration checks')
    def test_chapter_two_superscript_stays_with_description(self):
        section = extract_hts(os.environ['HTS_TEST_PDF'], page_numbers=[919])['sections'][0]
        row = next(line for line in section['layout_text'].splitlines() if '0201.10.50' in line)
        self.assertIn('Other', row)
        self.assertIn('1/', row)


if __name__ == '__main__':
    unittest.main()
