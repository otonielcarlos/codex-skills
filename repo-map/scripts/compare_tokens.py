#!/usr/bin/env python3
"""Compare paired baseline/repo-map runs from normalized JSONL usage records."""

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median


def compare(records, setup_tokens=0):
    pairs = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be an object")
        if not isinstance(record.get("task"), str) or not record["task"]:
            raise ValueError("each record needs a nonempty task")
        for field in ("run", "input_tokens", "output_tokens"):
            if type(record.get(field)) is not int or record[field] < 0:
                raise ValueError(f"{field} must be a nonnegative integer")
        if type(record.get("correct")) is not bool:
            raise ValueError("correct must be a boolean")
        mode = record.get("mode")
        if mode not in {"baseline", "repo-map"}:
            raise ValueError("mode must be baseline or repo-map")
        pair = pairs.setdefault((record["task"], record["run"]), {})
        if mode in pair:
            raise ValueError("duplicate task/run/mode")
        pair[mode] = record
    if type(setup_tokens) is not int or setup_tokens < 0:
        raise ValueError("setup_tokens must be a nonnegative integer")
    included = [pair for pair in pairs.values()
                if set(pair) == {"baseline", "repo-map"} and all(r["correct"] for r in pair.values())]
    if not included:
        raise ValueError("no complete pairs with both results marked correct")
    def totals(record):
        return record["input_tokens"] + record["output_tokens"]

    baseline = [totals(pair["baseline"]) for pair in included]
    mapped = [totals(pair["repo-map"]) for pair in included]
    baseline_total = sum(baseline)
    mapped_total = sum(mapped) + setup_tokens
    delta = median([totals(pair["baseline"]) - totals(pair["repo-map"]) for pair in included])
    quality = {}
    for mode in ("baseline", "repo-map"):
        runs = [pair[mode] for pair in pairs.values() if mode in pair]
        correct = sum(record["correct"] for record in runs)
        quality[mode] = {"runs": len(runs), "correct": correct,
                         "success_rate": correct / len(runs) if runs else None}
    return {
        "successful_pairs": len(included), "excluded_pairs": len(pairs) - len(included),
        "quality": quality,
        "baseline_tokens": baseline_total, "repo_map_tokens": sum(mapped),
        "setup_tokens": setup_tokens, "saved_tokens": baseline_total - mapped_total,
        "savings_percent": round(100 * (1 - mapped_total / baseline_total), 2) if baseline_total else None,
        "median_baseline_tokens": median(baseline), "median_repo_map_tokens": median(mapped),
        "median_paired_saved_tokens": delta,
        "break_even_queries_estimate": math.ceil(setup_tokens / delta) if delta > 0 else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, help="JSONL normalized usage records")
    parser.add_argument("--setup-tokens", type=int, default=0,
                        help="One-time index setup tokens, excluded from individual runs")
    args = parser.parse_args(argv)
    try:
        records = [json.loads(line) for line in args.records.read_text().splitlines() if line.strip()]
        print(json.dumps(compare(records, args.setup_tokens), indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"compare-tokens: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
