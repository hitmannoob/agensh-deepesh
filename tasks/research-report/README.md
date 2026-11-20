# Research-report task pack

A team researches a question from a goal and delivers a cited report. It works the
way ArcticSwarm does: an orchestrator splits the goal into tasks, builders gather
evidence, reviewers check it, and the orchestrator writes the report from verified
findings. The team uses the shared context board and nothing else: no repository,
no issues, no chat between agents. See [board-only teams](../../agensh/README.md#board-only-teams)
for the pack settings this uses.

## Project file

```toml
pack = "research-report"
name = "gpu-costs"
goal = """Compare the cost per million tokens of serving a 70B open model on
H100, H200 and B200, rented and owned, as of 2026. Audience: an infra lead
deciding what to buy. 3,000-5,000 words with a summary table."""

[workspace]
seed = "empty"

[team]
workers = 4

[budget]
hours = 1

[environment]
network = "open"
```

A team needs at least 2 workers.

## Roles

| Role | Workers | Does |
|---|---|---|
| Orchestrator | worker 1 | Posts `TASK`s, marks `KEY` claims, opens alternative tasks, answers `CHALLENGE`s, writes the `REPORT` |
| Builder | the rest | One task at a time: gathers evidence as `FACT`s, checks it, posts `DONE`; reviews between tasks |
| Reviewer | the last `max(1, workers // 4)` of a team of 3 or more | Checks findings against their sources: `VERIFIED`, `CHALLENGE` or `ALTERNATIVE` |

There is no acceptance step: the last `REPORT` is delivered as posted. Builders and reviewers
read pages through opencode subagents (`[environment] subagents`), one source at a time, so
fetched pages stay out of their own context, and builders post each finding as a `FACT` before
they open the next source. The prepare hook writes each worker's name into the prompts. The roles, the entry
types and the isolated and collaborative tasks are described to the workers in
[`prompts/agents.txt`](prompts/agents.txt) and [`templates/`](templates/).

## Results

The export hook reads the whole board from the team's database:

| File | Holds |
|---|---|
| `evidence.json` | Every board entry with its detail, in order |
| `delivery.json` | The delivered `REPORT` (label, version, author) and the entry counts, or `"report": null` |
| `_deliver/` | The last `REPORT` as `report.md`, with `README.md` (the goal) |

The evaluate hook keeps `report.md` in `$AGENSH_TASK_OUT`. It checks nothing and writes no
`acceptance.json`.
