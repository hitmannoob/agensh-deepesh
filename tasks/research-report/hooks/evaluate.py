#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(os.environ['AGENSH_ROOT'])


def log(message):
    print(f'[research-report] {message}', file=sys.stderr, flush=True)


def main():
    task_out = Path(os.environ['AGENSH_TASK_OUT'])
    if not (task_out / '_deliver' / 'report.md').is_file():
        (task_out / 'acceptance.json').write_text(json.dumps(
            {'head': None, 'all_passed': False, 'results': [], 'error': 'no REPORT on the board'}, indent=2) + '\n')
        log('no report to check')
        return 0
    status = subprocess.run([sys.executable, str(ROOT / 'tasks/software-project/hooks/evaluate.py')]).returncode
    for name in ('report.md', 'grade.json'):
        if (task_out / '_deliver' / name).is_file():
            shutil.copy2(task_out / '_deliver' / name, task_out / name)
            log(f'kept {task_out / name}')
    return status


if __name__ == '__main__':
    sys.exit(main())
