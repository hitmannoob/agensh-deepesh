#!/usr/bin/env python3
"""Check the report's sections: every figure cites a source, every source can be checked.

    python3 checks/lint.py

A section is sections/NN-<slug>.md and starts with a `## ` heading. A paragraph, list
item or table row that states a figure (a number such as $2.49, 3,000 tok/s or 80 GB;
not a year or a name like H100 or 70B) cites a footnote, [^1]. Each footnote is defined
in the same section, either as a source:

    [^1]: https://example.com/pricing — "the exact text that supports the figure" (accessed 2026-11-19)

or as a calculation from other footnotes:

    [^c1]: calc — $2.99/hr [^1] / 2,400 tok/s [^2] = $0.35 per million tokens
"""
from collections import Counter
from pathlib import Path
import re
import sys

SECTION_NAME = re.compile(r'\d{2}-[a-z0-9-]+\.md')
REFERENCE = re.compile(r'\[\^([A-Za-z0-9_-]+)\](?!:)')
DEFINITION = re.compile(r'^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$')
SOURCE = re.compile(r'https?://\S+.*"[^"]{10,}".*\(accessed \d{4}-\d{2}-\d{2}\)\s*$')
CALCULATION = re.compile(r'^calc\b.*\[\^[A-Za-z0-9_-]+\]')
FIGURE = re.compile(r'(?<![\w.])[$€£]?\d+(?:,\d{3})*(?:\.\d+)?(?!\w|-[A-Za-z])')
YEAR = re.compile(r'^(19|20)\d{2}$')
VERSION = re.compile(r'[A-Z][\w-]*\s$')
PLACEHOLDER = re.compile(r'\b(TODO|TBD|FIXME|XXX)\b|lorem ipsum', re.IGNORECASE)
TABLE_SEPARATOR = re.compile(r'^\|?\s*:?-{3,}')
LIST_ITEM = re.compile(r'^\s*([-*+]|\d+\.)\s+')
MAX_WORDS = 1500


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


def check_section(path):
    errors = []
    lines = path.read_text().splitlines()
    where = lambda number: f'{path}:{number}'
    if not SECTION_NAME.fullmatch(path.name):
        errors.append(f'{path}: name it sections/NN-<slug>.md (two digits, lowercase, hyphens)')
    first = next(((n, l) for n, l in enumerate(lines, 1) if l.strip()), None)
    if not first or not first[1].startswith('## '):
        errors.append(f'{where(first[0] if first else 1)}: start the section with a `## ` heading')
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
            if not SOURCE.match(body) and not CALCULATION.match(body):
                errors.append(f'{where(number)}: [^{name}] needs `<url> — "<quote of 10+ characters>" '
                              f'(accessed YYYY-MM-DD)` or `calc — <arithmetic citing footnotes>`')
        references.update(REFERENCE.findall(line))
    for name in references:
        if name not in definitions:
            errors.append(f'{path}: [^{name}] is cited but not defined in this section')
    for name, (number, _) in definitions.items():
        if name not in references:
            errors.append(f'{where(number)}: [^{name}] is defined but never cited')
    for number, text in claims(lines):
        if states_a_figure(text) and not REFERENCE.search(text):
            errors.append(f'{where(number)}: a figure without a citation: {text[:100]}')
    body = [line for line in lines if not DEFINITION.match(line.strip())]
    words = len(' '.join(body).split())
    if words > MAX_WORDS:
        errors.append(f'{path}: {words} words; keep a section under {MAX_WORDS} (split it)')
    return errors, len(definitions)


def main():
    sections = sorted(Path('sections').glob('*.md'))
    errors, sources = [], 0
    for path in sections:
        found, count = check_section(path)
        errors += found
        sources += count
    numbers = Counter(path.name[:2] for path in sections if SECTION_NAME.fullmatch(path.name))
    for number, count in sorted(numbers.items()):
        if count > 1:
            errors.append(f'sections/: {count} sections are numbered {number}; renumber one (see outline.md)')
    if Path('outline.md').is_file():
        for number, line in enumerate(Path('outline.md').read_text().splitlines(), 1):
            if PLACEHOLDER.search(line):
                errors.append(f'outline.md:{number}: placeholder text: {line.strip()[:80]}')
    for error in errors:
        print(error)
    print(f'{len(sections)} sections, {sources} footnotes: '
          + (f'{len(errors)} problem(s)' if errors else 'ok'))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
