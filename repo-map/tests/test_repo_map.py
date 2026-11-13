"""Behavioral tests against temporary Git worktrees; no network or model needed."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repo_map.py"
spec = importlib.util.spec_from_file_location("repo_map", SCRIPT)
repo_map = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repo_map)


class RepoMapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args,
                                 "--root", str(self.root), "--json"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_symbols_imports_and_reverse_impact(self):
        self.write("src/user.ts", "export class User { save() {} }\nexport const createUser = () => new User();")
        self.write("src/index.ts", "export { User, createUser } from './user.js';")
        self.write("src/app.ts", "import { User } from './index';\nexport function start() { return new User(); }")
        found = self.run_cli("find", "User")
        self.assertEqual({row["name"] for row in found["results"]}, {"User", "createUser"})
        self.assertTrue(all(row["line"] >= 1 for row in found["results"]))
        deps = self.run_cli("deps", "src/index.ts")["results"]
        self.assertEqual((deps[0]["target"], deps[0]["kind"]), ("src/user.ts", "reexport"))
        impact = self.run_cli("impact", "src/user.ts", "--depth", "2")["results"]
        self.assertEqual([(row["file"], row["depth"]) for row in impact],
                         [("src/index.ts", 1), ("src/app.ts", 2)])

    def test_incremental_edit_delete_and_restore_resolve_unchanged_importer(self):
        dependency = self.write("dep.ts", "export function original() {}")
        self.write("app.ts", "import { original } from './dep';")
        self.assertEqual(self.run_cli("build")["index"]["updated"], 2)
        self.assertEqual(self.run_cli("build")["index"]["updated"], 0)
        dependency.write_text("export function replaced() {}")
        result = self.run_cli("find", "original")
        self.assertEqual(result["index"]["updated"], 1)
        self.assertEqual(result["results"], [])
        dependency.unlink()
        result = self.run_cli("deps", "app.ts")
        self.assertEqual(result["index"]["deleted"], 1)
        self.assertEqual(result["results"][0]["status"], "unresolved")
        self.write("dep.ts", "export function restored() {}")
        result = self.run_cli("deps", "app.ts")
        self.assertEqual(result["index"]["updated"], 1)
        self.assertEqual(result["results"][0]["target"], "dep.ts")

    def test_gitignore_exclusions_and_symlinks(self):
        self.write(".gitignore", "ignored/\n")
        self.write("ignored/a.ts", "function ignored() {}")
        self.write("node_modules/pkg/index.js", "function vendor() {}")
        self.write("dist/out.js", "function compiled() {}")
        self.write("keep.ts", "function keep() {}")
        (self.root / "link.ts").symlink_to(self.root / "keep.ts")
        self.assertEqual(self.run_cli("build")["index"]["files"], 1)

    def test_alias_precedence_and_changes(self):
        self.write("src/a.ts", "export const a = 1;")
        self.write("other/a.ts", "export const a = 2;")
        self.write("app.ts", "import { a } from '@/a';")
        self.write(".repo-map.json", json.dumps({"aliases": {"@/*": ["src/*"]}}))
        self.assertEqual(self.run_cli("deps", "app.ts")["results"][0]["target"], "src/a.ts")
        self.write(".repo-map.json", json.dumps({"aliases": {"@/*": ["src/*"], "@/a": ["other/a.ts"]}}))
        result = self.run_cli("deps", "app.ts")
        self.assertEqual(result["index"]["updated"], 0)
        self.assertEqual(result["results"][0]["target"], "other/a.ts")

    def test_cycles_depth_and_bounded_results(self):
        self.write("a.ts", "import './b';\nexport function same() {}")
        self.write("b.ts", "import './a';\nexport function same() {}")
        self.write("c.ts", "import './b';\nexport function same() {}")
        result = self.run_cli("impact", "a.ts", "--depth", "1")
        self.assertEqual([row["file"] for row in result["results"]], ["b.ts"])
        result = self.run_cli("impact", "a.ts", "--depth", "20")
        self.assertEqual([row["file"] for row in result["results"]], ["b.ts", "c.ts"])
        result = self.run_cli("find", "same", "--limit", "1")
        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["truncated"])
        result = self.run_cli("impact", "a.ts", "--limit", "1")
        self.assertTrue(result["truncated"])

    def test_tsx_jsx_commonjs_and_dynamic_imports(self):
        self.write("view.tsx", "export const View = () => <div />;")
        self.write("widget.jsx", "export function Widget() { return <span />; }")
        self.write("app.cts", "import View = require('./view');\nconst other = require('./widget');\n"
                   "import('./missing');\nimport(variable);\nrequire('node:fs');")
        result = self.run_cli("deps", "app.cts")
        rows = result["results"]
        self.assertEqual([row["status"] for row in rows],
                         ["resolved", "resolved", "unresolved", "dynamic", "external"])
        self.assertEqual(self.run_cli("find", "Widget")["results"][0]["file"], "widget.jsx")

    def test_parse_errors_and_oversized_files_are_visible(self):
        self.write("bad.ts", "export function broken( {")
        self.write("huge.ts", " " * (repo_map.MAX_BYTES + 1))
        self.write("app.ts", "import './bad';")
        result = self.run_cli("build")
        self.assertEqual(result["coverage"]["skipped_files"], 2)
        self.assertEqual({row["status"] for row in result["results"]}, {"syntax_error", "oversized"})
        self.assertEqual(self.run_cli("find", "broken")["results"], [])
        self.write("bad.ts", "export function fixed() {}")
        self.assertEqual(self.run_cli("deps", "app.ts")["results"][0]["status"], "resolved")

    def test_paths_and_literal_search_do_not_expand_scope(self):
        self.write("a.ts", "export function exists() {}")
        self.assertEqual(self.run_cli("find", "%")["results"], [])
        self.assertEqual(self.run_cli("find", "' OR 1=1 --")["results"], [])
        self.assertIn("inside --root", self.run_cli("deps", "../outside.ts", success=False)["error"])
        self.assertIn("not indexed", self.run_cli("deps", "missing.ts", success=False)["error"])

    def test_invalid_alias_configuration_fails_clearly(self):
        self.write(".repo-map.json", '{"aliases":{"@/*":["../outside/*"]}}')
        self.assertIn("inside --root", self.run_cli("build", success=False)["error"])
        self.assertFalse((self.root / ".repo-map").exists())

    def test_failed_refresh_rolls_back_previous_index(self):
        self.write("a.ts", "export function before() {}")
        with closing(repo_map.connect(self.root)) as db:
            repo_map.refresh(db, self.root)
            self.write("a.ts", "export function after() {}")
            self.write("z.ts", "export function last() {}")
            from unittest.mock import patch
            original = Path.read_bytes

            def fail(path):
                if path.name == "z.ts":
                    raise OSError("simulated read failure")
                return original(path)

            with patch.object(Path, "read_bytes", fail), self.assertRaises(OSError):
                repo_map.refresh(db, self.root)
            self.assertEqual([row[0] for row in db.execute("SELECT name FROM symbols")], ["before"])

    def test_nested_project_scope(self):
        self.write("outside.ts", "export function outside() {}")
        self.write("nested/inside.ts", "export function inside() {}")
        self.assertEqual(repo_map.discover(self.root / "nested"), ["inside.ts"])

    def test_directory_index_and_extension_substitution(self):
        self.write("module/index.ts", "export function item() {}")
        self.write("worker.mts", "export function work() {}")
        self.write("app.ts", "import './module';\nimport './worker.mjs';")
        self.assertEqual([row["target"] for row in self.run_cli("deps", "app.ts")["results"]],
                         ["module/index.ts", "worker.mts"])

    def test_escaped_static_specifiers_are_reported(self):
        self.write("app.ts", r"import './\u0061';")
        result = self.run_cli("deps", "app.ts")
        self.assertEqual(result["results"][0]["status"], "unsupported")
        self.assertEqual(result["coverage"]["unsupported_imports"], 1)

    def test_incompatible_cache_requires_rebuild(self):
        with closing(repo_map.connect(self.root)) as db:
            repo_map.refresh(db, self.root)
            db.execute("UPDATE meta SET value = 'future' WHERE key = 'version'")
            db.commit()
        self.assertIn("incompatible index", self.run_cli("build", success=False)["error"])

    def test_non_git_directory_fails_without_creating_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SCRIPT), "build", directory, "--json"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Git worktree", json.loads(result.stdout)["error"])
            self.assertFalse((Path(directory) / ".repo-map").exists())


if __name__ == "__main__":
    unittest.main()
