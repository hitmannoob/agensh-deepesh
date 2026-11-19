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
pr = ["python3 checks/lint.py"]
main = ["python3 checks/lint.py", "python3 checks/build.py"]
final = ["python3 checks/lint.py", "python3 checks/build.py --complete"]

[team]
workers = 3

[coordination]
planning = true
'''

SECTION = '''## Rental prices

Lambda lists the H100 SXM at $2.99 per GPU-hour on demand.[^1] Llama 3.1 70B fits at 8-bit.

| GPU | $/GPU-hr |
|---|---|
| H100 SXM | 2.99 [^1] |

Per million tokens that is about $0.35.[^c1]

[^1]: https://lambda.ai/pricing — "H100 SXM $2.99 / GPU / hr" (accessed 2026-11-19)
[^c1]: calc — $2.99/hr [^1] / (2,400 tok/s × 3,600 s) × 10^6 = $0.35
'''


def git(*arguments, cwd=None):
    return subprocess.run(['git', *arguments], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class ResearchReportTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.project_file = base / 'project.toml'
        self.project_file.write_text(PROJECT)
        self.env_file = base / '.env.research-report-gpu-costs'
        self.env_file.write_text(f'AGENSH_PROJECT_FILE={self.project_file}\nAGENT_IMAGE=unused\n')
        self.task_out = base / 'out' / 'gpu-costs'
        self.task_out.mkdir(parents=True)

    def prepare(self):
        env = dict(os.environ, AGENSH_ROOT=str(ROOT), AGENSH_ENV_FILE=str(self.env_file),
                   AGENSH_TASK_OUT=str(self.task_out), RUN_ID='unit')
        result = subprocess.run([sys.executable, str(ROOT / 'tasks/research-report/hooks/prepare.py')],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return Path((self.task_out / '.seed_git').read_text().strip())

    def check(self, clone, *command):
        return subprocess.run([sys.executable, *command], cwd=clone, capture_output=True, text=True)

    def test_pack_takes_project_files_and_plans_with_its_own_prompt(self):
        pack = load_pack('research-report')
        self.assertTrue(pack.project)
        self.assertEqual(pack.planning, ROOT / 'tasks/research-report/prompts/planning.txt')
        project = load_project(self.project_file)
        self.assertEqual((project.profile, project.planning), ('research-report-gpu-costs', True))

    def test_prepare_seeds_the_checks_and_renders_the_researchers_prompts(self):
        clone = self.prepare()
        self.assertEqual(git('log', '--format=%s', cwd=clone).splitlines(),
                         ['Add the report checks and rubric', 'Add the Agensh team workflow', 'Start gpu-costs'])
        self.assertEqual(sorted(git('show', '--name-only', '--format=', 'HEAD', cwd=clone).splitlines()),
                         ['.gitignore', 'checks/build.py', 'checks/grade.py', 'checks/lint.py', 'rubric.md'])
        prompts = self.task_out / 'prompts'
        self.assertEqual(sorted(path.name for path in prompts.iterdir()),
                         ['delivery.txt', 'focus.txt', 'objective.txt', 'role.txt', 'work_cycle.txt'])
        self.assertEqual((prompts / 'role.txt').read_text(), 'researchers\n')
        self.assertIn('Compare what it costs', (prompts / 'objective.txt').read_text())
        self.assertIn('`python3 checks/lint.py`', (prompts / 'work_cycle.txt').read_text())
        self.assertNotIn('${', ''.join(path.read_text() for path in prompts.iterdir()))

    def test_seeded_checks_pass_a_cited_section_and_reject_an_uncited_figure(self):
        clone = self.prepare()
        self.assertEqual(self.check(clone, 'checks/lint.py').returncode, 0)
        (clone / 'sections').mkdir()
        (clone / 'outline.md').write_text('# GPU costs\n\n- sections/01-summary.md: Summary\n'
                                          '- sections/02-rental.md: Rental prices\n')
        (clone / 'sections/02-rental.md').write_text(SECTION)
        lint = self.check(clone, 'checks/lint.py')
        self.assertEqual(lint.returncode, 0, lint.stdout)
        built = self.check(clone, 'checks/build.py')
        self.assertEqual(built.returncode, 0, built.stdout)
        report = (clone / 'report.md').read_text()
        self.assertTrue(report.startswith('# GPU costs\n'))
        self.assertIn('$2.99 per GPU-hour on demand.[^02-1]', report)
        self.assertEqual(self.check(clone, 'checks/build.py', '--complete').returncode, 1)
        (clone / 'sections/02-rental.md').write_text(SECTION + '\nOwning one costs about $30,000.\n')
        lint = self.check(clone, 'checks/lint.py')
        self.assertEqual(lint.returncode, 1)
        self.assertIn('a figure without a citation: Owning one costs about $30,000.', lint.stdout)


if __name__ == '__main__':
    unittest.main()
