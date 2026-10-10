"""Anonymous filesystem smoke checks for the documented template layout.

These checks exercise copies and path isolation, not Claude Code or Codex dialogue.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'templates'
CLIENT = TEMPLATES / '顧客' / '_テンプレート'
CASE = CLIENT / '案件' / '_テンプレート'


def copy_missing(source: Path, target: Path):
    """Model the documented copy-only-if-absent step in an anonymous workspace."""
    for path in source.rglob('*'):
        dest = target / path.relative_to(source)
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def new_client(workspace: Path, client_id: str):
    target = workspace / '顧客' / client_id
    if target.exists():
        raise FileExistsError(target)
    shutil.copytree(CLIENT, target)
    return target


def new_case(client: Path, case_id: str):
    target = client / '案件' / case_id
    if target.exists():
        raise FileExistsError(target)
    shutil.copytree(CASE, target)
    return target


class AnonymousWorkspaceSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix='kit-smoke-')
        self.workspace = Path(self.tempdir.name) / 'company'
        self.workspace.mkdir()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_first_copy_and_resume_preserve_existing_edits(self):
        existing = self.workspace / 'AGENTS.md'
        existing.write_text('本人が記入した内容\n')
        copy_missing(TEMPLATES, self.workspace)
        self.assertEqual(existing.read_text(), '本人が記入した内容\n')
        self.assertTrue((self.workspace / '導入状態.md').exists())
        self.assertTrue((self.workspace / '役割/_役割テンプレート.md').exists())
        state = self.workspace / '導入状態.md'
        state.write_text('状態: 未完了\n回答済み: 匿名の工務店\n')
        copy_missing(TEMPLATES, self.workspace)
        self.assertEqual(state.read_text(), '状態: 未完了\n回答済み: 匿名の工務店\n')
        self.assertEqual(existing.read_text(), '本人が記入した内容\n')

    def test_multiple_clients_cases_and_same_name_do_not_collide(self):
        copy_missing(TEMPLATES, self.workspace)
        a, b = new_client(self.workspace, 'C001'), new_client(self.workspace, 'C002')
        a1, a2, b1 = new_case(a, 'P001'), new_case(a, 'P002'), new_case(b, 'P001')
        for case in (a1, a2, b1):
            (case / 'README.md').write_text('# 同名の匿名案件\n')
            for folder in ('議事録', '図面', '見積'):
                self.assertTrue((case / folder / 'README.md').exists())
        self.assertEqual(len({a1.resolve(), a2.resolve(), b1.resolve()}), 3)
        marker = a1 / '経過ログ.md'
        marker.write_text('本人の既存ログ\n')
        with self.assertRaises(FileExistsError):
            new_case(a, 'P001')
        self.assertEqual(marker.read_text(), '本人の既存ログ\n')
        self.assertNotEqual(a1.parent.parent, b1.parent.parent)

    def test_meeting_and_drawing_revisions_stay_in_the_case(self):
        copy_missing(TEMPLATES, self.workspace)
        a, b = new_client(self.workspace, 'C001'), new_client(self.workspace, 'C002')
        target, other = new_case(a, 'P001'), new_case(b, 'P001')
        meeting_dir = target / '議事録'
        first = meeting_dir / '2026-10-09_01.md'
        second = meeting_dir / '2026-10-09_02.md'
        shutil.copy2(meeting_dir / '_議事録テンプレート.md', first)
        first.write_text(first.read_text() + '\n決定: 匿名の例\n')
        shutil.copy2(meeting_dir / '_議事録テンプレート.md', second)
        self.assertIn('決定: 匿名の例', first.read_text())
        self.assertTrue(second.exists())
        drawing_dir = target / '図面'
        original, revision = drawing_dir / '平面図_原本.txt', drawing_dir / '平面図_改訂1.txt'
        original.write_text('原本\n')
        revision.write_text('改訂1\n')
        self.assertEqual(original.read_text(), '原本\n')
        ledger = drawing_dir / 'README.md'
        self.assertIn('未確認', ledger.read_text())
        ledger.write_text(ledger.read_text().replace('（未確認。人の確認後に更新）', '平面図_改訂1.txt'))
        self.assertIn('平面図_改訂1.txt', ledger.read_text())
        self.assertNotIn('匿名の例', (other / '議事録/README.md').read_text())
        self.assertEqual(list((other / '図面').iterdir()), [other / '図面/README.md'])

    def test_local_role_and_manual_are_reachable_without_source_repo(self):
        copy_missing(TEMPLATES, self.workspace)
        role = self.workspace / '役割' / 'estimate-review.md'
        role.write_text('''# 積算確認\n\n- 役割ID: estimate-review\n- 担当する仕事と境界: 案件の積算のみ確認\n- 入力: 対象案件の積算と図面台帳\n- 成果物: 案件の経過ログに指摘\n- 止めて人に確認する条件: 図面の採用版が不明\n- 関連する手順書: ../手順書/積算確認.md\n''')
        manual = self.workspace / '手順書' / '積算確認.md'
        manual.write_text('# 積算確認\n')
        agents = self.workspace / 'AGENTS.md'
        agents.write_text(agents.read_text() + '\n| estimate-review | 役割/estimate-review.md | 手順書/積算確認.md | 匿名確認 |\n')
        for relative in ('役割/estimate-review.md', '手順書/積算確認.md'):
            self.assertIn(relative, agents.read_text())
            self.assertTrue((self.workspace / relative).is_file())
        role_manual = role.parent / '../手順書/積算確認.md'
        self.assertTrue(role_manual.resolve().is_file())
        self.assertNotIn('CLAUDE_PLUGIN_ROOT', role.read_text())


if __name__ == '__main__':
    unittest.main()
