# Measure token savings

Use real model usage records, not characters divided by four or the number of files opened. An index can reduce tool output and still cost more overall on a small task.

## Paired protocol

1. Freeze the target revision and task wording. Keep model/version, reasoning settings, tool permissions and token budgets equal. Use fresh sessions; alternate which mode runs first. Record these settings with your experiment.
2. Use several realistic tasks: locate a symbol, explain a flow, inspect change impact, implement a small change. Define expected answers/tests before running. Repeat each task at least three times in each mode.
3. Baseline uses normal targeted search. Treatment uses this skill, including its loaded instructions, commands, errors and tool outputs. Judge correctness with the same rubric without revealing the mode. Incorrect or incomplete pairs are excluded from savings calculations and counted separately; also report each mode's success rate so exclusion cannot hide regressions.
4. Export actual input/output token usage for every model call, including any child agents. Sum repeated tool output when it appears in later model inputs: the provider's usage already accounts for it. Do not add tool-text token estimates on top of input usage. Normalize provider fields carefully: cached inputs must count once, and reasoning tokens already included in output must not be counted again. Store input/output separately because their monetary rates differ.
5. Separate cold setup from warm queries. Local CPU work uses no model tokens, but instructions and tool calls/results consumed by a model do. Record setup tokens once with `--setup-tokens`, or include setup inside a cold run; never both. Include incremental refreshes in the measured runs. Also record elapsed time and failures separately.

## Normalized usage

One JSON object per line, one line per completed session (sum all calls first):

```jsonl
{"task":"locate-user","run":1,"mode":"baseline","input_tokens":12000,"output_tokens":900,"correct":true}
{"task":"locate-user","run":1,"mode":"repo-map","input_tokens":7000,"output_tokens":800,"correct":true}
```

These numbers demonstrate the format; they are not benchmark results. Pairing uses `task` and `run`. The collector/exporter depends on the host's usage telemetry; this tool does not automatically capture sessions.

```bash
python3 repo-map/scripts/compare_tokens.py /path/to/runs.jsonl --setup-tokens 1500
```

The script reports combined token totals, campaign savings including setup once, per-mode medians and correctness rates, median paired savings, excluded pairs and estimated break-even queries. It rejects duplicate records and malformed usage. Missing/incorrect pairs are excluded from savings but remain in correctness rates. A zero baseline gives an undefined savings percentage (`null`); a nonpositive median saving gives no break-even estimate (`null`). A zero setup cost with positive median savings gives break-even 0.

`savings_percent = 100 × (1 − (repo_map_tokens + setup_tokens) / baseline_tokens)`

Break-even assumes future tasks resemble this measured mix; it is an estimate, not a promise. Report cold and warm results and savings per task type alongside correctness rates. Token totals are not dollar costs: calculate those separately using the actual model rates and cached-input billing for each run.
