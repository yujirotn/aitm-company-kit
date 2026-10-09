import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates' / '顧客' / '_テンプレート' / '案件' / '_テンプレート'


class RepositoryContractTests(unittest.TestCase):
    def test_manifest_names_versions_and_commands(self):
        plugin = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        self.assertEqual(plugin['name'], market['plugins'][0]['name'])
        self.assertEqual(plugin['version'], market['plugins'][0]['version'])
        for command in ('company-setup', 'new-client', 'new-case', 'meeting-note', 'drawing-revision', 'log'):
            self.assertTrue((ROOT / 'commands' / f'{command}.md').is_file())
            self.assertIn(f'/{command}', (ROOT / 'README.md').read_text())

    def test_template_references_and_isolation(self):
        required = ('README.md', '経過ログ.md', 'やりとり.md', '議事録/README.md',
                    '議事録/_議事録テンプレート.md', '図面/README.md', '見積/README.md')
        for relative in required:
            self.assertTrue((TEMPLATE / relative).is_file(), relative)
        self.assertTrue((ROOT / 'templates/導入状態.md').is_file())
        self.assertTrue((ROOT / 'templates/会社設定.md').is_file())
        self.assertTrue((ROOT / 'templates/顧客/_テンプレート/案件/案件一覧.md').is_file())
        for client, case in [('C001', 'P001'), ('C001', 'P002'), ('C002', 'P001')]:
            path = Path('顧客') / client / '案件' / case
            self.assertEqual(path.parts[1], client)
            self.assertEqual(path.parts[3], case)
        texts = '\n'.join(p.read_text() for p in (ROOT / 'commands').glob('*.md'))
        for path in ('templates/顧客/_テンプレート/',
                     'templates/顧客/_テンプレート/案件/_テンプレート/'):
            self.assertIn(path, texts)
        self.assertNotIn('templates/案件/', texts)

    def test_stop_and_history_contract(self):
        setup = (ROOT / 'commands/company-setup.md').read_text()
        self.assertIn('未完了', setup)
        self.assertIn('再設定', setup)
        self.assertIn('上書き', setup)
        self.assertIn('承認', setup)
        drawing = (ROOT / 'commands/drawing-revision.md').read_text()
        meeting = (ROOT / 'commands/meeting-note.md').read_text()
        self.assertIn('原本', drawing)
        self.assertIn('改訂', drawing)
        self.assertIn('最新版', drawing)
        for word in ('決定', '未決', '担当', '期限', '次アクション'):
            self.assertIn(word, meeting)
        for name in ('new-client', 'new-case', 'log', 'meeting-note', 'drawing-revision'):
            self.assertRegex((ROOT / 'commands' / f'{name}.md').read_text(), '曖昧|不明|未確認')

    def test_price_definitions_and_example(self):
        cost, rate = 100, 0.2
        self.assertEqual(cost / (1 - rate), 125)
        self.assertEqual(cost * (1 + rate), 120)
        quote = (ROOT / 'agents/quote-writer.md').read_text()
        self.assertIn('原価 / (1−g)', quote)
        self.assertIn('原価 × (1＋m)', quote)
        self.assertNotIn('原価に利益率を掛けて売価', quote)
        for term in ('税', '丸め', '仮単価', '確定単価'):
            self.assertIn(term, quote)

    def test_no_real_customer_files(self):
        self.assertFalse((ROOT / '顧客').exists())
        self.assertNotIn('山田', '\n'.join(p.read_text() for p in (ROOT / 'templates').rglob('*.md')))


if __name__ == '__main__':
    unittest.main()
