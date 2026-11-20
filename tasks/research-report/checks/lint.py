#!/usr/bin/env python3
"""Check report.md: every figure cites a source, every source can be checked.

    python3 checks/lint.py [report.md]

The report starts with a `# ` title. A paragraph, list item or table row that states a
figure (a number such as $2.49, 3,000 tok/s or 80 GB; not a year or a name like H100 or 70B)
cites a footnote, [^1]. Each footnote is defined once and cited at least once, either as a
source on the web or in an uploaded document:

    [^1]: https://example.com/pricing — "the exact text that supports the figure" (accessed 2026-11-19)
    [^2]: doc:docs/vendor-quote.pdf p.4 — "the exact text that supports the figure"

or as a calculation from other footnotes:

    [^c1]: calc — $2.99/hr [^1] / 2,400 tok/s [^2] = $0.35 per million tokens
"""
from collections import Counter
from pathlib import Path
import re
import sys

REFERENCE = re.compile(r'\[\^([A-Za-z0-9_-]+)\](?!:)')
DEFINITION = re.compile(r'^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$')
SOURCE = re.compile(r'https?://\S+.*"[^"]{10,}".*\(accessed \d{4}-\d{2}-\d{2}\)\s*$')
DOCUMENT = re.compile(r'doc:\S+.*"[^"]{10,}"')
CALCULATION = re.compile(r'^calc\b.*\[\^[A-Za-z0-9_-]+\]')
FIGURE = re.compile(r'(?<![\w.])[$€£]?\d+(?:,\d{3})*(?:\.\d+)?(?!\w|-[A-Za-z])')
YEAR = re.compile(r'^(19|20)\d{2}$')
VERSION = re.compile(r'[A-Z][\w-]*\s$')
PLACEHOLDER = re.compile(r'\b(TODO|TBD|FIXME|XXX)\b|lorem ipsum', re.IGNORECASE)
TABLE_SEPARATOR = re.compile(r'^\|?\s*:?-{3,}')
LIST_ITEM = re.compile(r'^\s*([-*+]|\d+\.)\s+')


def is_figure(text, match):
    value = match.group(0)
    if YEAR.match(value):
        return False
    return not ('.' in value and value[0].isdigit() and VERSION.search(text[:match.start()]))


def states_a_figure(text):
    text = REFERENCE.sub('', text)
    return any(is_figure(text, match) for match in FIGURE.finditer(text))


def claims(lines):
    paragraph, start = [], 0
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        block = (not stripped or stripped.startswith('#') or stripped.startswith('|')
                 or LIST_ITEM.match(line) or DEFINITION.match(stripped))
        if block and paragraph:
            yield start, ' '.join(paragraph)
            paragraph = []
        if stripped.startswith('|'):
            header = number < len(lines) and TABLE_SEPARATOR.match(lines[number].strip())
            if not TABLE_SEPARATOR.match(stripped) and not header:
                yield number, stripped
        elif LIST_ITEM.match(line):
            yield number, stripped
        elif not block:
            if not paragraph:
                start = number
            paragraph.append(stripped)
    if paragraph:
        yield start, ' '.join(paragraph)


def check(path):
    errors = []
    lines = path.read_text().splitlines()
    where = lambda number: f'{path}:{number}'
    first = next(((n, l) for n, l in enumerate(lines, 1) if l.strip()), None)
    if not first or not first[1].startswith('# '):
        errors.append(f'{where(first[0] if first else 1)}: start the report with a `# ` title')
    definitions, references = {}, Counter()
    for number, line in enumerate(lines, 1):
        if PLACEHOLDER.search(line):
            errors.append(f'{where(number)}: placeholder text: {line.strip()[:80]}')
        definition = DEFINITION.match(line.strip())
        if definition:
            name, body = definition.groups()
            if name in definitions:
                errors.append(f'{where(number)}: footnote [^{name}] is defined twice')
            definitions[name] = (number, body)
            if not SOURCE.match(body) and not DOCUMENT.match(body) and not CALCULATION.match(body):
                errors.append(f'{where(number)}: [^{name}] needs `<url> — "<quote of 10+ characters>" '
                              f'(accessed YYYY-MM-DD)`, `doc:<path> p.<n> — "<quote>"` or '
                              f'`calc — <arithmetic citing footnotes>`')
        references.update(REFERENCE.findall(line))
    for name in references:
        if name not in definitions:
            errors.append(f'{path}: [^{name}] is cited but not defined')
    for name, (number, _) in definitions.items():
        if name not in references:
            errors.append(f'{where(number)}: [^{name}] is defined but never cited')
    for number, text in claims(lines):
        if states_a_figure(text) and not REFERENCE.search(text):
            errors.append(f'{where(number)}: a figure without a citation: {text[:100]}')
    return errors, len(definitions)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else 'report.md')
    if not path.is_file():
        print(f'{path}: no report')
        return 1
    errors, sources = check(path)
    for error in errors:
        print(error)
    print(f'{path}: {sources} footnotes: ' + (f'{len(errors)} problem(s)' if errors else 'ok'))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
