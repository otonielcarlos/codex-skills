# codex-skills

A small collection of Codex skills that reduce unnecessary work and token usage without sacrificing correctness.

## Skills

- **concise-coding** — Searches narrowly, reads only relevant context, validates proportionally, and reports briefly.
- **surgical-edits** — Produces the smallest correct diff while preserving unrelated code.
- **repo-map** — Finds JS/TS symbols and traces file dependencies with an incremental local index.

## Principle

Search precisely. Change only what is necessary. Validate according to risk. Report briefly.

## Workflow

I use Astra or Fable for complex planning, then Sol 6.1 or Opus 5.5 to implement well-defined tasks. I follow each provider's model guidance and use these skills to keep context and changes focused.

This workflow has kept my $20/month subscription sufficient.

## Install

Install all skills:

```bash
npx skills add otonielcarlos/codex-skills
```

Install one skill:

```bash
npx skills add otonielcarlos/codex-skills --skill concise-coding
npx skills add otonielcarlos/codex-skills --skill surgical-edits
npx skills add otonielcarlos/codex-skills --skill repo-map
```

## Repo Map

Find the code. Trace its dependencies. Read only what matters.

From this collection's root, with [uv](https://docs.astral.sh/uv/) and Git installed:

```bash
uv run --locked --project repo-map python repo-map/scripts/repo_map.py find createUser --root /path/to/project
uv run --locked --project repo-map python repo-map/scripts/repo_map.py impact src/users/service.ts --root /path/to/project
```

```text
repo-map / impact / 2 results
18 files | 0 updated | 0 deleted

  src/users/routes.ts:3  depth 1 via src/users/service.ts
  src/app.ts:5  depth 2 via src/users/routes.ts
```

Illustrative output. Every query refreshes the local SQLite index. Add `--json` for bounded machine-readable results. Supports JS/TS symbols, imports and reexports; unresolved and dynamic relationships are reported. Impact results are review candidates, not a safety guarantee.

See [commands, aliases and limits](repo-map/references/commands.md) and the [token measurement protocol](repo-map/references/benchmark.md). Token savings must be measured; none are claimed here.
