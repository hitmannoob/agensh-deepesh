#!/usr/bin/env python3
"""Grade report.md against rubric.md with a model, through AGENSH_MODEL_BASE.

    python3 checks/build.py && python3 checks/grade.py --model MODEL [--min 3.5]

The model scores each rubric criterion from 1 to 5. Writes grade.json; fails when
the mean score is below --min.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

CRITERION = re.compile(r'^- \*\*([a-z-]+)\*\*', re.MULTILINE)
INSTRUCTIONS = """You grade a research report against a rubric. Check the report's figures
against the quotes its footnotes give, and its claims against each other. Reply with one
JSON object only: {"scores": {"<criterion>": <1-5>, ...}, "summary": "<two sentences>",
"problems": ["<specific problem, naming the section>", ...]}."""


def ask(base, model, goal, rubric, report):
    body = {'model': model, 'messages': [
        {'role': 'system', 'content': INSTRUCTIONS},
        {'role': 'user', 'content': f'# Goal\n\n{goal}\n\n# Rubric\n\n{rubric}\n\n# Report\n\n{report}'}]}
    request = urllib.request.Request(f'{base.rstrip("/")}/chat/completions', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=600) as response:
        text = json.load(response)['choices'][0]['message']['content']
    found = re.search(r'\{.*\}', text, re.DOTALL)
    if not found:
        raise ValueError(f'no JSON in the reply: {text[:200]}')
    return json.loads(found.group(0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--min', type=float, default=3.5)
    args = parser.parse_args()
    base = os.environ.get('AGENSH_MODEL_BASE')
    if not base:
        print('not graded: AGENSH_MODEL_BASE is not set, so there is no model to grade with')
        return 2
    if not Path('report.md').is_file():
        print('not graded: no report.md; run python3 checks/build.py first')
        return 2
    rubric = Path('rubric.md').read_text()
    criteria = CRITERION.findall(rubric)
    try:
        grade = ask(base, args.model, Path('README.md').read_text(), rubric, Path('report.md').read_text())
    except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
        print(f'not graded: {error}')
        return 2
    scores = {name: grade.get('scores', {}).get(name) for name in criteria}
    unscored = [name for name, score in scores.items() if not isinstance(score, (int, float))]
    if unscored:
        print(f'not graded: the model gave no score for {", ".join(unscored)}')
        return 2
    mean = round(sum(scores.values()) / len(scores), 2)
    Path('grade.json').write_text(json.dumps({'model': args.model, 'mean': mean, 'min': args.min, **grade,
                                              'scores': scores}, indent=2) + '\n')
    for name, score in scores.items():
        print(f'{name}: {score}')
    print(f'mean {mean} (min {args.min}): {grade.get("summary", "")}')
    for problem in grade.get('problems', []):
        print(f'- {problem}')
    return 0 if mean >= args.min else 1


if __name__ == '__main__':
    sys.exit(main())
