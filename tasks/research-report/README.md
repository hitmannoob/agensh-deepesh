# Research-report task pack

A team researches a question from a goal and delivers a cited report. The report
is a repository: one markdown file per section under `sections/`, merged through
PRs like code, and built into `report.md`. The core runtime is described in
[`agensh/`](../../agensh/README.md); this pack reuses the
[software-project](../software-project/README.md) hooks for import, sync and
delivery.

## Project file

The fields are software-project's. A typical project:

```toml
pack = "research-report"
name = "gpu-costs"
goal = """Compare the cost per million tokens of serving a 70B open model on
H100, H200 and B200, rented and owned, as of 2026. Audience: an infra lead
deciding what to buy. 3,000-5,000 words with a summary table."""

[workspace]
seed = "empty"

[acceptance]
pr = ["python3 checks/lint.py"]
main = ["python3 checks/lint.py", "python3 checks/build.py"]
final = ["python3 checks/lint.py", "python3 checks/build.py --complete",
         "python3 checks/grade.py --model openai/gpt-6-luna"]

[team]
workers = 4

[coordination]
planning = true
planning_timeout = "15m"

[budget]
hours = 1

[environment]
network = "open"
```

Turn planning on. Worker 1 then opens one issue per section and writes
`outline.md` before the others wake, so they do not all start on the same
obvious searches.

## What the team gets

The prepare hook runs software-project's, then commits from [`seed/`](seed/):

| File | Does |
|---|---|
| `checks/lint.py` | Every figure in a paragraph, list item or table row cites a footnote; every footnote is a source (`<url> — "<quote>" (accessed YYYY-MM-DD)`) or a calculation citing other footnotes; no placeholders; no two sections share a number; sections stay under 1,500 words |
| `checks/build.py` | Joins `sections/*.md` in file-name order into `report.md`, renaming footnotes per section; `--complete` also fails when a section `outline.md` lists is missing |
| `checks/grade.py` | Scores `report.md` against `rubric.md` with a model through `AGENSH_MODEL_BASE`; writes `grade.json`; exits 1 below `--min` (default 3.5) and 2 when it could not grade |
| `rubric.md` | The grader's criteria: coverage, support, sources, conflicts, usefulness |
| `.gitignore` | `report.md` and `grade.json`, which are built, never committed |

`checks/**` and `rubric.md` are protected, so no PR can loosen the checks that gate it.

Workers are `researchers` in the core prompt (`templates/role.txt`). Each claims a
section, posts confirmed figures as board `FACT`s with their URL, and writes the
section with footnotes. `main` must keep passing `lint.py` and `build.py`; whether
the report is complete and good is judged only at the end, by the `final` commands.

## Results

After evaluation, `report.md` and `grade.json` (when graded) are copied from the
delivered checkout into `$AGENSH_TASK_OUT`. The delivered repository or bundle holds
the sources (`outline.md`, `sections/`); `python3 checks/build.py` rebuilds the report.
