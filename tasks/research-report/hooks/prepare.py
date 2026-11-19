#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(os.environ['AGENSH_ROOT'])
SEED = Path(__file__).resolve().parents[1] / 'seed'
IDENTITY = ['-c', 'user.name=Agensh', '-c', 'user.email=agensh@localhost']


def log(message):
    print(f'[research-report] {message}', file=sys.stderr, flush=True)


def main():
    status = subprocess.run([sys.executable, str(ROOT / 'tasks/software-project/hooks/prepare.py')]).returncode
    if status:
        return status
    clone = Path((Path(os.environ['AGENSH_TASK_OUT']) / '.seed_git').read_text().strip())
    added = []
    for source in sorted(path for path in SEED.rglob('*') if path.is_file() and '__pycache__' not in path.parts):
        relative = source.relative_to(SEED)
        if (clone / relative).exists():
            log(f'{relative} already exists in the repository; keeping it')
            continue
        (clone / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, clone / relative)
        added.append(str(relative))
    if added:
        subprocess.run(['git', *IDENTITY, 'add', *added], cwd=clone, check=True)
        subprocess.run(['git', *IDENTITY, 'commit', '--quiet', '-m', 'Add the report checks and rubric'],
                       cwd=clone, check=True)
        log(f'added {", ".join(added)}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        log(f'FATAL: {error}')
        sys.exit(1)
