#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(os.environ['AGENSH_ROOT'])
sys.path.insert(0, str(ROOT / 'tasks/software-project/hooks'))

from common import context  # noqa: E402
from agensh import roles  # noqa: E402


def log(message):
    print(f'[research-report] {message}', file=sys.stderr, flush=True)


def names(org, workers):
    return ', '.join(f'`{org}-worker{n}`' for n in workers) or 'none'


def main():
    task_out, values, project, _ = context()
    if project.workers < 2:
        raise RuntimeError('a research team needs at least 2 workers: an orchestrator and a builder')
    status = subprocess.run([sys.executable, str(ROOT / 'tasks/software-project/hooks/prepare.py')]).returncode
    if status:
        return status
    org = values['ORG_NAME']
    team = {
        'ORCHESTRATOR': names(org, [1]),
        'BUILDERS': names(org, roles.builders(project.workers)),
        'REVIEWERS': names(org, roles.reviewers(project.workers)),
    }
    for path in sorted((task_out / 'prompts').glob('*.txt')):
        text = path.read_text()
        for key, value in team.items():
            text = text.replace('${%s}' % key, value)
        path.write_text(text)
    log(f'roles: orchestrator {team["ORCHESTRATOR"]}, builders {team["BUILDERS"]}, '
        f'reviewers {team["REVIEWERS"]}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        log(f'FATAL: {error}')
        sys.exit(1)
