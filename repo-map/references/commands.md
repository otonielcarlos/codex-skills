# Commands and boundaries

All paths below assume the current directory is this collection's root. When installed elsewhere, replace `repo-map` with the absolute skill directory. Quote paths containing spaces.

```bash
uv run --locked --project repo-map python repo-map/scripts/repo_map.py build /path/to/project
uv run --locked --project repo-map python repo-map/scripts/repo_map.py find User --root /path/to/project
uv run --locked --project repo-map python repo-map/scripts/repo_map.py deps src/app.ts --root /path/to/project
uv run --locked --project repo-map python repo-map/scripts/repo_map.py impact src/user.ts --root /path/to/project --depth 3 --json
```

Plain text is the default; `--json` returns one bounded object with `command`, refresh counters in `index`, `coverage`, `results`, and `truncated`. Errors exit with status 1; JSON mode emits an `error` object. Invalid CLI arguments exit with status 2. `build` lists skipped files; an empty result means the index is ready, possibly with zero supported files.

`find` is a case-insensitive substring search (SQLite's built-in ASCII case folding). Results include the declaration's name, kind, file and line range; duplicate names remain distinct. `deps` reports source lines, specifiers, relation kinds, resolved targets and statuses. `impact` uses breadth-first traversal: one result per file, shortest discovered depth, and the next file toward the changed file in `via`. Its default depth is 2, maximum 20. All commands accept `--limit` from 1 to 200.

## Scope and freshness

- Git-tracked and untracked, nonignored `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.mts`, `.cts` files under `--root` are eligible. Git must be installed and the directory must be inside a worktree. No repository hooks or project code are executed.
- Dependency/build/cache directories are excluded even if tracked: `node_modules`, `vendor`, `dist`, `build`, `coverage`, `.next`, `.venv`, `.git`, `.repo-map`. Symlinks and paths outside the root are excluded. Uninitialized submodules are not indexed.
- Syntax errors and files larger than 2 MiB are skipped and counted. Syntax recovery is deliberately not treated as reliable dependency data.
- Each query enumerates eligible files and hashes their contents. Only changed files are parsed. Deleted file records cascade to their symbols/imports. All stored import relationships are re-resolved after refresh, including unchanged importers; this catches newly added targets and alias changes.
- Refreshes are transactional. A read/parse failure aborts the query rather than quietly using an old map. A repository changing during the scan is not an atomic filesystem snapshot; rerun after edits settle.
- SQLite stores hashes, names, file paths, source ranges and import specifiers, not source bodies. Add `.repo-map/` to the target's `.gitignore` yourself when appropriate; the script does not edit it. Delete the cache to rebuild if its schema is incompatible.

## Resolution

Supported edges: static ES imports, `export ... from`, literal `import('...')`, literal `require('...')`, and TypeScript `import x = require('...')`. Nonliteral call arguments are marked `dynamic`. CommonJS `require` is recognized syntactically; a locally shadowed function named `require` can produce a false relationship.

Relative imports try exact paths, supported extensions and directory indexes. `.js`/`.jsx`/`.mjs`/`.cjs` specifiers also try corresponding TypeScript source extensions. This is a navigation heuristic, not the TypeScript compiler or a runtime module resolver. Extensionless resolution tries TS before JS; validate the source when both exist.

For aliases, create `.repo-map.json` at the target root:

```json
{
  "aliases": {
    "@/*": ["src/*"],
    "@users": ["src/users/index.ts"],
    "shared/*": ["packages/shared/src/*", "src/shared/*"]
  }
}
```

Targets are root-relative, tried in order, and cannot escape the root. Exact patterns win; otherwise the longest matching wildcard prefix wins. Each pattern accepts at most one `*`. Config changes take effect on the next query.

The index does not interpret `tsconfig.json`, package exports/imports, workspace packages, bundler aliases, or runtime loaders. Translate relevant mappings into `.repo-map.json`. Unmapped bare specifiers are labeled `external`; this can include internal workspace packages. Unresolved relative or configured-alias imports are labeled `unresolved`. Escaped static import strings are labeled `unsupported`; escaped call arguments are counted as `dynamic`. Absolute specifiers, computed paths, non-code assets, call binding, CommonJS export assignments and symbol-level reference resolution are outside this version's scope. Anonymous declarations without a declared name are not returned by `find`.

## Validation

From the collection root:

```bash
uv run --locked --project repo-map python -m unittest discover -s repo-map/tests -v
```

The tests use temporary Git worktrees and cover incremental refreshes, failure rollback, aliases, reexports, cycles, dynamic imports, exclusions and bounded CLI output. When extraction semantics change, bump `SCHEMA_VERSION` so an old cache cannot silently retain outdated relationships.
