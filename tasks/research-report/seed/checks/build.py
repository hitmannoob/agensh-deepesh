#!/usr/bin/env python3
"""Build report.md from sections/*.md in file-name order.

    python3 checks/build.py              build what is there
    python3 checks/build.py --complete   also fail when a section outline.md lists is missing

The title is outline.md's `# ` heading, else README.md's. Footnotes are renamed per
section ([^1] in 03-costs.md becomes [^03-1]) so sections cannot collide.
"""
from pathlib import Path
import re
import sys

REFERENCE = re.compile(r'\[\^([A-Za-z0-9_-]+)\]')
PLANNED = re.compile(r'sections/(\d{2}-[a-z0-9-]+\.md)')


def title(*paths):
    for path in map(Path, paths):
        if path.is_file():
            for line in path.read_text().splitlines():
                if line.startswith('# '):
                    return line[2:].strip()
    return 'Report'


def main():
    complete = '--complete' in sys.argv[1:]
    sections = sorted(Path('sections').glob('*.md'))
    outline = Path('outline.md').read_text() if Path('outline.md').is_file() else ''
    missing = [name for name in dict.fromkeys(PLANNED.findall(outline)) if not Path('sections', name).is_file()]
    parts = [f'# {title("outline.md", "README.md")}']
    for path in sections:
        prefix = path.name[:2]
        parts.append(REFERENCE.sub(lambda match: f'[^{prefix}-{match.group(1)}]', path.read_text().strip()))
    report = '\n\n'.join(parts) + '\n'
    Path('report.md').write_text(report)
    print(f'report.md: {len(sections)} sections, {len(report.split())} words'
          + (f'; missing from outline.md: {", ".join(missing)}' if missing else ''))
    if complete and (missing or not sections):
        print('incomplete: ' + ('no sections' if not sections else f'{len(missing)} planned section(s) missing'))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
