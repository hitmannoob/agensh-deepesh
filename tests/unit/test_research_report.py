import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agensh.pack import load_pack  # noqa: E402
from agensh.project import load_project  # noqa: E402

PROJECT = '''pack = "research-report"
name = "gpu-costs"
goal = "Compare what it costs to serve a 70B model on H100 and B200."

[workspace]
seed = "empty"

[acceptance]
final = ["python3 checks/lint.py"]

[team]
workers = 4
'''

REPORT = '''# GPU costs

Lambda lists the H100 SXM at $2.99 per GPU-hour on demand.[^1] A vendor quote puts a B200 at $41,000.[^2]

| GPU | $/GPU-hr |
|---|---|
| H100 SXM | 2.99 [^1] |

Per million tokens that is about $0.35.[^c1]

[^1]: https://lambda.ai/pricing — "H100 SXM $2.99 / GPU / hr" (accessed 2026-11-19)
[^2]: doc:docs/vendor-quote.pdf p.4 — "B200 list price $41,000 per GPU"
[^c1]: calc — $2.99/hr [^1] / (2,400 tok/s × 3,600 s) × 10^6 = $0.35
'''

FAKE_DOCKER = '''#!/bin/sh
case "$1" in
  ps) echo omcgitea-research-report-gpu-costs-mysql-1 ;;
  exec) case "$*" in
          *--default-character-set=utf8mb4*) cat "$BOARD_ROWS" ;;
          *) iconv -f UTF-8 -t CP1252 "$BOARD_ROWS" ;;
        esac ;;
esac
'''


class ResearchReportTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.project_file = base / 'project.toml'
        self.project_file.write_text(PROJECT)
        self.env_file = base / '.env.research-report-gpu-costs'
        self.env_file.write_text(f'AGENSH_PROJECT_FILE={self.project_file}\nAGENT_IMAGE=unused\nORG_NAME=team\n'
                                 'MYSQL_ROOT_PASSWORD=x\n')
        self.task_out = base / 'out' / 'gpu-costs'
        self.task_out.mkdir(parents=True)
        self.docker = base / 'docker'
        self.docker.write_text(FAKE_DOCKER)
        self.docker.chmod(0o755)
        self.rows = base / 'rows.json'

    def hook(self, name, **extra):
        env = dict(os.environ, AGENSH_ROOT=str(ROOT), AGENSH_ENV_FILE=str(self.env_file),
                   AGENSH_TASK_OUT=str(self.task_out), AGENSH_PROFILE='research-report-gpu-costs',
                   RUN_ID='unit', DOCKER=str(self.docker), BOARD_ROWS=str(self.rows), **extra)
        return subprocess.run([sys.executable, str(ROOT / f'tasks/research-report/hooks/{name}.py')],
                              env=env, capture_output=True, text=True)

    def lint(self, text):
        path = Path(self.directory.name) / 'report.md'
        path.write_text(text)
        return subprocess.run([sys.executable, str(ROOT / 'tasks/research-report/checks/lint.py'), str(path)],
                              capture_output=True, text=True)

    def test_pack_runs_the_team_on_the_board_without_gitea(self):
        pack = load_pack('research-report')
        self.assertEqual(pack.mcp_servers, ('board',))
        self.assertIn('TASK', pack.board_types)
        self.assertNotIn('CLAIM', pack.board_types)
        self.assertTrue(pack.task_wakeups)
        self.assertFalse(pack.ci_gate)
        self.assertEqual(pack.backlog, 'board')
        self.assertNotIn('sync', pack.hooks)
        self.assertEqual(pack.agents, ROOT / 'tasks/research-report/prompts/agents.txt')
        self.assertEqual(load_project(self.project_file).profile, 'research-report-gpu-costs')

    def test_prepare_names_each_role_in_the_prompts(self):
        result = self.hook('prepare')
        self.assertEqual(result.returncode, 0, result.stderr)
        prompts = self.task_out / 'prompts'
        self.assertEqual(sorted(path.name for path in prompts.iterdir()),
                         ['delivery.txt', 'objective.txt', 'work_cycle.txt'])
        roles = (prompts / 'work_cycle.txt').read_text()
        self.assertIn('**Orchestrator**: `team-worker1`.', roles)
        self.assertIn('**Builders**: `team-worker2`, `team-worker3`.', roles)
        self.assertIn('**Reviewers**: `team-worker4`.', roles)
        self.assertIn('Compare what it costs', (prompts / 'objective.txt').read_text())
        self.assertNotIn('${', ''.join(path.read_text() for path in prompts.iterdir()))

        env = dict(os.environ, AGENT_NAME='team-worker2', AGENSH_WORKERS='4')
        agents = subprocess.run(['bash', str(ROOT / 'agent/render_agents.sh'),
                                 str(ROOT / 'tasks/research-report/prompts/agents.txt'), str(prompts)],
                                env=env, capture_output=True, text=True, check=True).stdout
        self.assertIn('You are team-worker2, one of 4 agents', agents)
        self.assertIn('**Builders**: `team-worker2`', agents)
        self.assertIn('## The report', agents)
        self.assertNotIn('gitea', agents.lower())
        self.assertNotIn('${', agents)

    def test_prepare_refuses_a_team_of_one(self):
        self.project_file.write_text(PROJECT.replace('workers = 4', 'workers = 1'))
        result = self.hook('prepare')
        self.assertEqual(result.returncode, 1)
        self.assertIn('at least 2 workers', result.stderr)

    def test_lint_takes_curly_quotes_and_rejects_quotes_joined_with_an_ellipsis(self):
        curly = REPORT.replace('— "H100 SXM $2.99 / GPU / hr" (accessed 2026-11-19)',
                               '— “H100 SXM $2.99 / GPU / hr”. Accessed 2026-11-19.')
        lint = self.lint(curly)
        self.assertEqual(lint.returncode, 0, lint.stdout)
        for joined in ('"H100 SXM ... $2.99 / GPU / hr"', '“H100 SXM … $2.99 / GPU / hr”'):
            with self.subTest(joined=joined):
                lint = self.lint(REPORT.replace('"H100 SXM $2.99 / GPU / hr"', joined))
                self.assertEqual(lint.returncode, 1)
                self.assertIn('[^1] joins text with "..."', lint.stdout)

    def test_pack_checks_reports_on_the_board_and_reads_pages_through_subagents(self):
        pack = load_pack('research-report')
        self.assertEqual(pack.report_check, ROOT / 'tasks/research-report/checks/lint.py')
        self.assertTrue(pack.subagents)

    def test_lint_passes_a_cited_report_and_rejects_an_uncited_figure(self):
        lint = self.lint(REPORT)
        self.assertEqual(lint.returncode, 0, lint.stdout)
        lint = self.lint(REPORT + '\nOwning one costs about $30,000.\n')
        self.assertEqual(lint.returncode, 1)
        self.assertIn('a figure without a citation: Owning one costs about $30,000.', lint.stdout)
        lint = self.lint(REPORT.replace('# GPU costs', '## GPU costs'))
        self.assertIn('start the report with a `# ` title', lint.stdout)

    def test_export_delivers_the_latest_report_and_the_evidence(self):
        self.rows.write_text(json.dumps([
            {'id': 9, 'author': 'team-worker1', 'type': 'REPORT', 'content': 'v2: adds B200',
             'delegation_id': None, 'ts': 2.0, 'detail': REPORT},
            {'id': 3, 'author': 'team-worker2', 'type': 'FACT', 'content': 'Lambda H100 SXM $2.99/GPU-hr',
             'delegation_id': 't1', 'ts': 1.0, 'detail': 'https://lambda.ai/pricing — "H100 SXM $2.99"'},
            {'id': 5, 'author': 'team-worker1', 'type': 'REPORT', 'content': 'v1: first',
             'delegation_id': None, 'ts': 1.5, 'detail': '# old\n'},
        ], ensure_ascii=False), encoding='utf-8')
        result = self.hook('export')
        self.assertEqual(result.returncode, 0, result.stderr)
        deliver = self.task_out / '_deliver'
        self.assertEqual((deliver / 'report.md').read_text(), REPORT)
        self.assertTrue((deliver / 'checks/lint.py').is_file())
        self.assertTrue((deliver / 'rubric.md').is_file())
        self.assertIn('Compare what it costs', (deliver / 'README.md').read_text())
        delivery = json.loads((self.task_out / 'delivery.json').read_text())
        self.assertEqual(delivery['report']['label'], 'G9')
        self.assertEqual(delivery['report']['version'], 'v2')
        self.assertEqual(delivery['counts'], {'FACT': 1, 'REPORT': 2})
        evidence = json.loads((self.task_out / 'evidence.json').read_text())
        self.assertEqual([entry['label'] for entry in evidence], ['G3', 'G5', 'G9'])

    def test_without_a_report_nothing_is_delivered_and_evaluation_says_so(self):
        self.rows.write_text('NULL\n')
        result = self.hook('export')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.task_out / '_deliver').exists())
        self.assertEqual(json.loads((self.task_out / 'delivery.json').read_text())['error'], 'no REPORT on the board')
        result = self.hook('evaluate')
        self.assertEqual(result.returncode, 0, result.stderr)
        acceptance = json.loads((self.task_out / 'acceptance.json').read_text())
        self.assertEqual((acceptance['all_passed'], acceptance['error']), (False, 'no REPORT on the board'))


if __name__ == '__main__':
    unittest.main()
