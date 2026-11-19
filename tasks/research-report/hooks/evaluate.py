#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(os.environ['AGENSH_ROOT'])


def main():
    status = subprocess.run([sys.executable, str(ROOT / 'tasks/software-project/hooks/evaluate.py')]).returncode
    task_out = Path(os.environ['AGENSH_TASK_OUT'])
    for name in ('report.md', 'grade.json'):
        if (task_out / '_deliver' / name).is_file():
            shutil.copy2(task_out / '_deliver' / name, task_out / name)
            print(f'[research-report] kept {task_out / name}', file=sys.stderr, flush=True)
    return status


if __name__ == '__main__':
    sys.exit(main())
