---
name: repo-map
description: Locate JavaScript/TypeScript symbols and inspect imports or reverse dependencies using an incremental local code index. Use for repository navigation and change-impact questions; use direct file reads for implementation details.
---

# Repo Map

Find the relevant code before reading it. Return source locations, then open only the ranges needed for the task.

## Run

Resolve `<skill>` to this skill's directory and `<repo>` to the target Git project. Requires Git, uv, and Python 3.10+; uv can provision Python. First use downloads the locked parser dependencies. Source indexing runs locally without an LLM or external service.

```bash
uv run --locked --project <skill> python <skill>/scripts/repo_map.py find createUser --root <repo> --json
uv run --locked --project <skill> python <skill>/scripts/repo_map.py deps src/users/service.ts --root <repo> --json
uv run --locked --project <skill> python <skill>/scripts/repo_map.py impact src/users/service.ts --root <repo> --depth 2 --json
```

- Queries automatically refresh `.repo-map/index.sqlite3` in the target project. Use `build <repo>` to inspect coverage without querying.
- Start with a narrow name or file. Results default to 20; `truncated` indicates omitted matches. Narrow the query before raising `--limit` (maximum 200).
- `find` searches function, class, method, interface, type and enum names by literal substring. It is not semantic search.
- `deps` returns direct imports/reexports; `impact` traverses reverse file dependencies. Impact results are candidates to inspect, not proof that a change is safe or that every candidate needs editing.
- Check `coverage` and dependency `status`. Unresolved, dynamic, skipped, external and runtime relationships can make impact results incomplete. Use targeted search and source reads to fill those gaps. Do not interpret no matches as proof of no dependencies.
- The cache excludes source bodies but contains symbol names and import paths. Keep `.repo-map/` out of version control. No source files or Git settings are changed by the indexer.
- For unsupported languages, known edit locations, or a small one-off lookup, use normal targeted search when building a map would add work.

Read [commands and resolution limits](references/commands.md) for aliases, scope, troubleshooting or contributing. Read [token measurement](references/benchmark.md) only when evaluating savings; do not infer token savings from output size or file counts.
