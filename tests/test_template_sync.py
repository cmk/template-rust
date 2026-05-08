from __future__ import annotations

import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SYNC_PATH = REPO_ROOT / "scripts" / "template_sync.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def parse_manifest(script_text: str, name: str) -> list[str]:
    """Extract a bash array literal of double-quoted strings from the script."""
    match = re.search(rf"^{re.escape(name)}=\((.*?)^\)", script_text, re.M | re.S)
    if not match:
        raise AssertionError(f"manifest array {name} not found in script")
    body = match.group(1)
    return re.findall(r'"([^"]+)"', body)


class TemplateSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script_text = TEMPLATE_SYNC_PATH.read_text(encoding="utf-8")
        cls.verbatim = parse_manifest(cls.script_text, "VERBATIM_PATHS")
        cls.surgical = parse_manifest(cls.script_text, "SURGICAL_PATHS")
        # Both sets must be non-empty for the tests to be meaningful.
        if not cls.verbatim or not cls.surgical:
            raise AssertionError("manifest arrays parsed empty")

    def _make_template(self, root: Path) -> None:
        """Create a fake template-rust working tree at `root`."""
        root.mkdir(parents=True, exist_ok=True)
        git(root, "init", "--initial-branch=main")
        git(root, "config", "user.name", "Template Sync Test")
        git(root, "config", "user.email", "tst@example.invalid")

        # Populate every manifest path with a deterministic stub.
        for rel in [*self.verbatim, *self.surgical]:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"template stub: {rel}\n", encoding="utf-8")

        # Overwrite the script entry with the real script content so
        # the manifest's self-reference doesn't run a stub. The
        # regression test stays a stub — the test isn't executed by
        # the script under test, so it doesn't need real content.
        sync = root / "scripts" / "template_sync.sh"
        sync.write_text(self.script_text, encoding="utf-8")
        sync.chmod(sync.stat().st_mode | stat.S_IXUSR)

        # Mark a hook file executable so test_apply_preserves_exec_bit
        # can verify the install -m mode round-trip.
        for hook in (".githooks/pre-commit", ".githooks/pre-push"):
            hp = root / hook
            hp.chmod(hp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

        # The marker file lives at the template root only; it must
        # not be in the manifest, so it's added explicitly here.
        (root / ".template-rust-root").write_text(
            "template fixture marker\n", encoding="utf-8"
        )

        git(root, "add", ".")
        git(root, "commit", "-m", "template fixture")

    def _make_downstream(self, root: Path, template: Path) -> None:
        """Create a downstream that exactly mirrors the template's manifest paths."""
        root.mkdir(parents=True, exist_ok=True)
        git(root, "init", "--initial-branch=main")
        git(root, "config", "user.name", "Template Sync Test")
        git(root, "config", "user.email", "tst@example.invalid")

        for rel in [*self.verbatim, *self.surgical]:
            src = template / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

        git(root, "add", ".")
        git(root, "commit", "-m", "downstream fixture")

    def _run_sync(
        self, template: Path, *args: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(template / "scripts" / "template_sync.sh"), *args],
            cwd=template,
            capture_output=True,
            text=True,
        )

    def test_pristine_downstream_reports_match_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            r = self._run_sync(template, str(downstream))

            self.assertEqual(r.returncode, 0, msg=f"stdout={r.stdout!r} stderr={r.stderr!r}")
            self.assertNotIn(": drift\n", r.stdout)
            self.assertNotIn(": missing downstream\n", r.stdout)

    def test_edited_verbatim_path_reports_drift_and_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            target = self.verbatim[0]
            (downstream / target).write_text("DOWNSTREAM EDITED\n", encoding="utf-8")
            git(downstream, "add", target)
            git(downstream, "commit", "-m", "downstream drift")

            r = self._run_sync(template, str(downstream))

            self.assertEqual(r.returncode, 1, msg=f"stdout={r.stdout!r}")
            self.assertIn(f"  {target}: drift", r.stdout)
            self.assertIn("DOWNSTREAM EDITED", r.stdout)

    def test_missing_verbatim_path_reports_missing_and_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            target = self.verbatim[1]
            (downstream / target).unlink()
            git(downstream, "add", "-A")
            git(downstream, "commit", "-m", "remove verbatim path")

            r = self._run_sync(template, str(downstream))

            self.assertEqual(r.returncode, 1)
            self.assertIn(f"  {target}: missing downstream", r.stdout)

    def test_apply_writes_drifted_file_and_skips_surgical(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            verbatim_target = self.verbatim[0]
            surgical_target = self.surgical[0]
            (downstream / verbatim_target).write_text("DRIFT\n", encoding="utf-8")
            (downstream / surgical_target).write_text("SURGICAL DRIFT\n", encoding="utf-8")
            git(downstream, "add", "-A")
            git(downstream, "commit", "-m", "downstream drift")

            r = self._run_sync(template, "--apply", str(downstream))

            self.assertEqual(r.returncode, 0, msg=f"stderr={r.stderr!r}")
            # Verbatim path was overwritten with template content.
            self.assertEqual(
                (downstream / verbatim_target).read_text(encoding="utf-8"),
                (template / verbatim_target).read_text(encoding="utf-8"),
            )
            # Surgical path was left alone (still says "SURGICAL DRIFT").
            self.assertEqual(
                (downstream / surgical_target).read_text(encoding="utf-8"),
                "SURGICAL DRIFT\n",
            )
            self.assertIn("differs (surgical merge required)", r.stdout)

    def test_apply_preserves_exec_bit_on_hook(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            hook = ".githooks/pre-commit"
            # Strip exec bits on the downstream copy and make its
            # content drift so --apply must rewrite the file.
            (downstream / hook).chmod(0o644)
            (downstream / hook).write_text("downstream drift\n", encoding="utf-8")
            git(downstream, "add", hook)
            git(downstream, "commit", "-m", "downstream drift on hook")

            r = self._run_sync(template, "--apply", str(downstream))

            self.assertEqual(r.returncode, 0, msg=f"stderr={r.stderr!r}")
            applied_mode = (downstream / hook).stat().st_mode
            template_mode = (template / hook).stat().st_mode
            self.assertEqual(
                stat.S_IMODE(applied_mode), stat.S_IMODE(template_mode),
                msg="--apply should preserve template's file mode (exec bit)",
            )
            self.assertTrue(
                applied_mode & stat.S_IXUSR,
                msg="hook should be executable after --apply",
            )

    def test_apply_refuses_dirty_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            (downstream / self.verbatim[0]).write_text("DIRTY\n", encoding="utf-8")
            # Note: not committed — working tree is dirty.

            r = self._run_sync(template, "--apply", str(downstream))

            self.assertEqual(r.returncode, 2)
            self.assertIn("refusing --apply on dirty downstream", r.stderr)

    def test_non_git_downstream_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            self._make_template(template)
            non_git = tmp / "not_a_repo"
            non_git.mkdir()

            r = self._run_sync(template, str(non_git))

            self.assertEqual(r.returncode, 2)
            self.assertIn("not a git working tree", r.stderr)

    def test_duplicate_downstream_argument_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            downstream = tmp / "downstream"
            self._make_template(template)
            self._make_downstream(downstream, template)

            r = self._run_sync(template, str(downstream), str(downstream))

            self.assertEqual(r.returncode, 2)
            self.assertIn("passed twice", r.stderr)

    def test_self_sync_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            self._make_template(template)

            r = self._run_sync(template, str(template))

            self.assertEqual(r.returncode, 2)
            self.assertIn("template-rust to itself", r.stderr)

    def test_no_arguments_prints_usage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            template = tmp / "template"
            self._make_template(template)

            r = self._run_sync(template)

            self.assertEqual(r.returncode, 2)
            self.assertIn("usage:", r.stderr)


if __name__ == "__main__":
    unittest.main()
