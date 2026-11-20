#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys


def log(message):
    print(f'[research-report] {message}', file=sys.stderr, flush=True)


def main():
    task_out = Path(os.environ['AGENSH_TASK_OUT'])
    report = task_out / '_deliver' / 'report.md'
    if not report.is_file():
        log('no report')
        return 0
    shutil.copy2(report, task_out / 'report.md')
    log(f'kept {task_out / "report.md"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
