#!/usr/bin/env python3
"""A local, incremental JavaScript/TypeScript dependency index."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from collections import deque
from contextlib import closing
from pathlib import Path, PurePosixPath

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser

SCHEMA_VERSION = "1"
EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs")
EXCLUDED = {".git", ".repo-map", ".venv", "node_modules", "dist", "build",
            "coverage", "vendor", ".next"}
MAX_BYTES = 2 * 1024 * 1024
SYMBOL_KINDS = {
    "function_declaration": "function", "generator_function_declaration": "function",
    "class_declaration": "class", "abstract_class_declaration": "class",
    "method_definition": "method", "method_signature": "method",
    "interface_declaration": "interface", "type_alias_declaration": "type",
    "enum_declaration": "enum",
}


def walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.named_children))


def text(node, source):
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def literal(node, source):
    """Only ordinary unescaped string literals are safe module specifiers."""
    if node is None or node.type != "string":
        return None
    raw = text(node, source)[1:-1]
    return raw if "\\" not in raw else None


class Extractor:
    def __init__(self):
        self.parsers = {
            "js": Parser(Language(tree_sitter_javascript.language())),
            "ts": Parser(Language(tree_sitter_typescript.language_typescript())),
            "tsx": Parser(Language(tree_sitter_typescript.language_tsx())),
        }

    def extract(self, path, source):
        suffix = PurePosixPath(path).suffix
        language = "tsx" if suffix == ".tsx" else (
            "ts" if suffix in {".ts", ".mts", ".cts"} else "js")
        tree = self.parsers[language].parse(source)
        if tree.root_node.has_error:
            return [], [], "syntax_error"
        symbols, dependencies = [], []
        for node in walk(tree.root_node):
            name = node.child_by_field_name("name")
            kind = SYMBOL_KINDS.get(node.type)
            if node.type == "variable_declarator":
                value = node.child_by_field_name("value")
                if value and value.type in {"arrow_function", "function_expression",
                                            "generator_function", "class"}:
                    kind = "class" if value.type == "class" else "function"
            if kind and name and name.type in {"identifier", "type_identifier",
                                               "property_identifier", "private_property_identifier"}:
                symbols.append((text(name, source), kind, node.start_point.row + 1,
                                node.end_point.row + 1))

            specifier, relation = None, None
            if node.type in {"import_statement", "export_statement"}:
                source_node = node.child_by_field_name("source")
                specifier = literal(source_node, source)
                relation = "reexport" if node.type == "export_statement" else "import"
                if source_node is not None and specifier is None:
                    dependencies.append(("<unsupported>", relation,
                                         node.start_point.row + 1, "unsupported"))
            elif node.type == "import_require_clause":
                specifier = literal(node.child_by_field_name("source"), source)
                relation = "require"
            elif node.type == "call_expression":
                function = node.child_by_field_name("function")
                arguments = node.child_by_field_name("arguments")
                if function and text(function, source) in {"require", "import"}:
                    args = arguments.named_children if arguments else []
                    relation = text(function, source)
                    specifier = literal(args[0], source) if len(args) == 1 else None
                    if specifier is None:
                        dependencies.append(("<dynamic>", relation,
                                             node.start_point.row + 1, "dynamic"))
            if specifier is not None:
                dependencies.append((specifier, relation, node.start_point.row + 1, None))
        return symbols, dependencies, "ok"


def discover(root):
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others",
         "--exclude-standard", "-z", "--", "."], capture_output=True, check=False)
    if result.returncode:
        raise ValueError("--root must be inside a Git worktree")
    paths = set()
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = Path(raw.decode("utf-8", errors="surrogateescape"))
        if path.suffix not in EXTENSIONS or EXCLUDED.intersection(path.parts):
            continue
        absolute = root / path
        if absolute.is_file() and not absolute.is_symlink() and absolute.resolve().is_relative_to(root):
            paths.add(path.as_posix())
    return sorted(paths)


def aliases_for(root):
    """Explicit root-relative mappings avoid guessing compiler/bundler semantics."""
    config = root / ".repo-map.json"
    if not config.exists():
        return {}
    data = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) - {"aliases"}:
        raise ValueError(".repo-map.json accepts only an 'aliases' object")
    aliases = data.get("aliases", {})
    if not isinstance(aliases, dict):
        raise ValueError("aliases must be an object of pattern: [target, ...]")
    for pattern, targets in aliases.items():
        if not pattern or pattern.count("*") > 1 or not isinstance(targets, list) or not targets:
            raise ValueError("alias patterns need at most one '*' and a nonempty target list")
        for target in targets:
            if (not isinstance(target, str) or not target or target.count("*") > pattern.count("*")
                    or Path(target).is_absolute() or ".." in PurePosixPath(target).parts):
                raise ValueError("alias targets must stay inside --root and match the pattern wildcard")
    return aliases


def normalize(path):
    parts = []
    for part in PurePosixPath(path).parts:
        if part == "..":
            if not parts:
                return None
            parts.pop()
        elif part not in {".", "/"}:
            parts.append(part)
    return "/".join(parts)


def candidates(base):
    suffix = PurePosixPath(base).suffix
    if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
        substitutions = {".js": (".ts", ".tsx"), ".jsx": (".tsx",),
                         ".mjs": (".mts",), ".cjs": (".cts",)}
        for replacement in substitutions[suffix]:
            yield base[:-len(suffix)] + replacement
    yield base
    if not suffix:
        yield from (base + extension for extension in EXTENSIONS)
        yield from (base + "/index" + extension for extension in EXTENSIONS)


def resolve(source, specifier, files, aliases):
    bases = []
    if specifier.startswith("."):
        bases.append(str(PurePosixPath(source).parent / specifier))
    else:
        # Exact mappings win; otherwise the longest matching wildcard prefix wins.
        patterns = sorted(aliases, key=lambda key: ("*" in key, -len(key.split("*")[0]), key))
        for pattern in patterns:
            if "*" in pattern:
                prefix, suffix = pattern.split("*")
                if not specifier.startswith(prefix) or not specifier.endswith(suffix):
                    continue
                if len(specifier) < len(prefix) + len(suffix):
                    continue
                match = specifier[len(prefix):len(specifier) - len(suffix) if suffix else None]
            elif pattern == specifier:
                match = ""
            else:
                continue
            bases.extend(target.replace("*", match) for target in aliases[pattern])
            break
    for base in bases:
        normalized = normalize(base)
        if normalized is not None:
            for candidate in candidates(normalized):
                if candidate in files:
                    return candidate, "resolved"
    return None, "unresolved" if bases or specifier.startswith((".", "/")) else "external"


def connect(root):
    directory = root / ".repo-map"
    if directory.is_symlink():
        raise ValueError(".repo-map must be a local directory, not a symlink")
    directory.mkdir(exist_ok=True)
    path = directory / "index.sqlite3"
    if path.is_symlink():
        raise ValueError("index.sqlite3 must not be a symlink")
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS symbols (
            file TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
            name TEXT NOT NULL, kind TEXT NOT NULL, line INTEGER NOT NULL, end_line INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS dependencies (
            source TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
            specifier TEXT NOT NULL, kind TEXT NOT NULL, line INTEGER NOT NULL,
            target TEXT, status TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS symbols_name ON symbols(name);
        CREATE INDEX IF NOT EXISTS dependencies_target ON dependencies(target);
        CREATE INDEX IF NOT EXISTS dependencies_source ON dependencies(source);
    """)
    version = db.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()
    if version and version[0] != SCHEMA_VERSION:
        db.close()
        raise ValueError("incompatible index; remove .repo-map/index.sqlite3 and rebuild")
    return db


def refresh(db, root):
    paths = discover(root)
    aliases = aliases_for(root)
    previous = {row["path"]: row["digest"] for row in db.execute("SELECT path, digest FROM files")}
    extractor = None
    updated = 0
    deleted = sorted(set(previous) - set(paths))
    # A failed refresh leaves the previous complete index intact.
    with db:
        for path in deleted:
            db.execute("DELETE FROM files WHERE path = ?", (path,))
        for path in paths:
            absolute = root / path
            if absolute.stat().st_size > MAX_BYTES:
                digest, status, symbols, dependencies = "oversized", "oversized", [], []
            else:
                source = absolute.read_bytes()
                digest = hashlib.sha256(source).hexdigest()
                if previous.get(path) == digest:
                    continue
                if extractor is None:
                    extractor = Extractor()
                symbols, dependencies, status = extractor.extract(path, source)
            if previous.get(path) == digest:
                continue
            updated += 1
            db.execute("DELETE FROM files WHERE path = ?", (path,))
            db.execute("INSERT INTO files VALUES (?, ?, ?)", (path, digest, status))
            db.executemany("INSERT INTO symbols VALUES (?, ?, ?, ?, ?)",
                           [(path, *symbol) for symbol in symbols])
            db.executemany("INSERT INTO dependencies VALUES (?, ?, ?, ?, NULL, ?)",
                           [(path, specifier, kind, line, hint or "unresolved")
                            for specifier, kind, line, hint in dependencies])
        # Re-resolve even unchanged importers after additions, deletions or alias edits.
        files = {row[0] for row in db.execute("SELECT path FROM files WHERE status = 'ok'")}
        for row in db.execute("SELECT rowid, * FROM dependencies").fetchall():
            if row["status"] in {"dynamic", "unsupported"}:
                continue
            target, status = resolve(row["source"], row["specifier"], files, aliases)
            if target != row["target"] or status != row["status"]:
                db.execute("UPDATE dependencies SET target = ?, status = ? WHERE rowid = ?",
                           (target, status, row["rowid"]))
        db.execute("INSERT OR REPLACE INTO meta VALUES ('version', ?)", (SCHEMA_VERSION,))
    return {"files": len(paths), "updated": updated, "deleted": len(deleted)}


def coverage(db):
    file_issues = db.execute("SELECT count(*) FROM files WHERE status != 'ok'").fetchone()[0]
    counts = dict(db.execute("SELECT status, count(*) FROM dependencies GROUP BY status"))
    return {"skipped_files": file_issues, "unresolved_imports": counts.get("unresolved", 0),
            "dynamic_imports": counts.get("dynamic", 0), "external_imports": counts.get("external", 0),
            "unsupported_imports": counts.get("unsupported", 0)}


def indexed_path(db, root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("file must be inside --root")
    relative = path.relative_to(root).as_posix()
    if not db.execute("SELECT 1 FROM files WHERE path = ?", (relative,)).fetchone():
        raise ValueError(f"file is not indexed: {relative}")
    return relative


def query(db, root, args):
    if args.command == "build":
        return [dict(row) for row in db.execute(
            "SELECT path AS file, status FROM files WHERE status != 'ok' ORDER BY path LIMIT ?",
            (args.limit + 1,))]
    if args.command == "find":
        return [dict(row) for row in db.execute("""
            SELECT file, name, kind, line, end_line FROM symbols
            WHERE instr(lower(name), lower(?)) > 0
            ORDER BY (name = ?) DESC, name, file, line LIMIT ?
        """, (args.name, args.name, args.limit + 1))]
    path = indexed_path(db, root, args.file)
    if args.command == "deps":
        return [dict(row) for row in db.execute("""
            SELECT source AS file, line, kind, specifier, target, status FROM dependencies
            WHERE source = ? ORDER BY line, specifier LIMIT ?
        """, (path, args.limit + 1))]
    seen, queue, rows = {path}, deque([(path, 0)]), []
    while queue:
        target, depth = queue.popleft()
        if depth >= args.depth:
            continue
        for row in db.execute("""
            SELECT source AS file, min(line) AS line FROM dependencies
            WHERE target = ? AND status = 'resolved' GROUP BY source ORDER BY source
        """, (target,)):
            if row["file"] in seen:
                continue
            seen.add(row["file"])
            rows.append({**dict(row), "depth": depth + 1, "via": target})
            if len(rows) > args.limit:
                return rows
            queue.append((row["file"], depth + 1))
    return rows


def bounded_int(maximum):
    def parse(value):
        number = int(value)
        if not 1 <= number <= maximum:
            raise argparse.ArgumentTypeError(f"must be between 1 and {maximum}")
        return number
    return parse


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, description in (("build", "Build or refresh the index"),
                              ("find", "Find symbols by literal name substring"),
                              ("deps", "List a file's imports and reexports"),
                              ("impact", "Find transitive reverse dependencies")):
        command = subparsers.add_parser(name, help=description)
        command.add_argument("--root", type=Path, default=Path.cwd(), help="Git project directory")
        command.add_argument("--json", action="store_true", help="Machine-readable bounded output")
        command.add_argument("--limit", type=bounded_int(200), default=20)
        if name == "build":
            command.add_argument("directory", type=Path, nargs="?")
        elif name == "find":
            command.add_argument("name")
        else:
            command.add_argument("file", help="Path relative to --root")
        if name == "impact":
            command.add_argument("--depth", type=bounded_int(20), default=2)
    return parser.parse_args(argv)


def render(result):
    update = result["index"]
    print(f"repo-map / {result['command']} / {len(result['results'])} results")
    print(f"{update['files']} files | {update['updated']} updated | {update['deleted']} deleted")
    print()
    for row in result["results"]:
        location = row["file"] + (f":{row['line']}" if "line" in row else "")
        if "name" in row:
            detail = f"{row['kind']} {row['name']}"
        elif "specifier" in row:
            detail = f"{row['kind']} {row['specifier']} -> {row['target'] or row['status']}"
        elif "via" in row:
            detail = f"depth {row['depth']} via {row['via']}"
        else:
            detail = row["status"]
        print(f"  {location}  {detail}")
    if not result["results"]:
        print("  No matches." if result["command"] != "build" else "  Index ready.")
    if result["truncated"]:
        print("\nMore results omitted; narrow the query or increase --limit (max 200).")
    issues = result["coverage"]
    if any(issues.values()):
        print("\nCoverage: " + " | ".join(f"{key}={value}" for key, value in issues.items() if value))
    if result["command"] == "impact":
        print("\nCandidates for review; unresolved, dynamic and runtime dependencies may be missing.")


def main(argv=None):
    args = arguments(argv)
    root = (getattr(args, "directory", None) or args.root).resolve()
    try:
        # Validate scope/config before creating the cache.
        discover(root)
        aliases_for(root)
        with closing(connect(root)) as db:
            stats = refresh(db, root)
            rows = query(db, root, args)
            result = {"command": args.command, "index": stats, "coverage": coverage(db),
                      "results": rows[:args.limit], "truncated": len(rows) > args.limit}
        if args.json:
            print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
        else:
            render(result)
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        if args.json:
            print(json.dumps({"error": str(error)}))
        else:
            print(f"repo-map: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
