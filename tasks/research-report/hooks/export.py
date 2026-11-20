#!/usr/bin/env python3
from collections import Counter
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(os.environ['AGENSH_ROOT'])
PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tasks/software-project/hooks'))

from common import context, write_json  # noqa: E402

QUERY = ("SELECT JSON_ARRAYAGG(JSON_OBJECT('id', id, 'author', thread_id, 'type', type, 'content', content, "
         "'delegation_id', delegation_id, 'ts', ts_epoch, 'detail', detail)) "
         "FROM board_gists WHERE board_id = '{board}'")


def log(message):
    print(f'[research-report] {message}', file=sys.stderr, flush=True)


def board_rows(values, profile, board_id):
    docker = shlex.split(os.environ.get('DOCKER', 'sudo -n docker'))
    found = subprocess.run([*docker, 'ps', '--filter', f'name=omcgitea-{profile}-mysql', '--format', '{{.Names}}'],
                           capture_output=True, text=True).stdout.split()
    if not found:
        raise RuntimeError(f'the team database for {profile} is not running')
    run = subprocess.run([*docker, 'exec', found[0], 'mysql', '-N', '-B', '--raw', '--default-character-set=utf8mb4',
                          '-uroot', f'-p{values.get("MYSQL_ROOT_PASSWORD", "")}', '-D', 'omcgitea',
                          '-e', QUERY.format(board=board_id)], capture_output=True, encoding='utf-8')
    if run.returncode != 0:
        raise RuntimeError(f'could not read the board: {run.stderr.strip()[-300:]}')
    text = run.stdout.strip()
    rows = json.loads(text) if text and text != 'NULL' else []
    return sorted(rows, key=lambda row: row['id'])


def evidence(rows):
    return [{'label': f'G{row["id"]}', 'author': row['author'], 'type': row['type'], 'content': row['content'],
             'delegation_id': row.get('delegation_id'), 'ts': row.get('ts'), 'detail': row.get('detail')}
            for row in rows]


def deliver(task_out, project, report):
    checkout = task_out / '_deliver'
    shutil.rmtree(checkout, ignore_errors=True)
    checkout.mkdir()
    (checkout / 'report.md').write_text(report['detail'].rstrip() + '\n')
    (checkout / 'README.md').write_text(f'# {project.name}\n\n{project.goal}')


def main():
    task_out, values, project, pack = context()
    rows = board_rows(values, os.environ['AGENSH_PROFILE'], pack.board_id)
    write_json(task_out / 'evidence.json', evidence(rows))
    reports = [row for row in rows if row['type'] == 'REPORT' and (row.get('detail') or '').strip()]
    record = {'mode': 'report', 'board_entries': len(rows), 'counts': dict(Counter(row['type'] for row in rows))}
    if not reports:
        shutil.rmtree(task_out / '_deliver', ignore_errors=True)
        write_json(task_out / 'delivery.json', {**record, 'report': None, 'error': 'no REPORT on the board'})
        log(f'no REPORT among {len(rows)} board entries; nothing to deliver')
        return 0
    latest = reports[-1]
    deliver(task_out, project, latest)
    write_json(task_out / 'delivery.json', {**record, 'report': {
        'label': f'G{latest["id"]}', 'version': latest['content'].split(':', 1)[0],
        'author': latest['author'], 'posted_at': latest.get('ts')}})
    log(f'delivering REPORT G{latest["id"]} ({latest["content"]}) from {len(rows)} board entries')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        log(f'FATAL: {error}')
        sys.exit(1)
