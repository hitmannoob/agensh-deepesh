import re

TASK = re.compile(r'^t\d+ (?:[a-z0-9-]+-)?worker(\d+) (isolated|collaborative):')


def reviewers(workers):
    if workers < 3:
        return []
    count = max(1, workers // 4)
    return list(range(workers - count + 1, workers + 1))


def builders(workers):
    return [n for n in range(2, workers + 1) if n not in reviewers(workers)]


def task_worker(content, workers):
    match = TASK.match(content or '')
    if not match or not 2 <= int(match.group(1)) <= workers:
        return None
    return int(match.group(1))


def wakeups(entries, workers, after):
    notices = {}
    for entry in entries:
        label = str(entry.get('_label') or '')
        if not label[1:].isdigit() or int(label[1:]) <= after:
            continue
        kind, content, author = entry.get('type'), str(entry.get('content', '')), str(entry.get('thread_id', ''))
        if kind == 'TASK':
            worker = task_worker(content, workers)
            recipients = [worker] if worker else []
        elif kind in ('DONE', 'CHALLENGE', 'ALTERNATIVE'):
            recipients = [1]
        elif kind == 'KEY':
            recipients = reviewers(workers) or builders(workers)
        else:
            recipients = []
        for worker in recipients:
            if not author.endswith(f'-worker{worker}'):
                notices.setdefault(worker, []).append((kind, label, author, content))
    return notices


def last_label(entries):
    return max((int(str(e.get('_label'))[1:]) for e in entries
                if str(e.get('_label') or '')[1:].isdigit()), default=0)
