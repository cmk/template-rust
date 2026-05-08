from __future__ import annotations

import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_PII_PATH = REPO_ROOT / "scripts" / "check_pii.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


class CheckPiiTests(unittest.TestCase):
    def test_allowlisted_staged_match_does_not_fail_under_set_e(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            home_path = "/Users/" + "alice" + "/project"
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "PII Test")
            git(repo, "config", "user.email", "pii@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "check_pii.sh"
            script.write_text(CHECK_PII_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            (repo / ".pii-allow").write_text(f"^path={home_path}$\n", encoding="utf-8")
            (repo / "README.md").write_text("safe\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "initial")

            (repo / "allowed.txt").write_text(f"path={home_path}\n", encoding="utf-8")
            git(repo, "add", "allowed.txt")

            result = subprocess.run(
                [str(script)],
                cwd=repo,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_tree_mode_detects_committed_home_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            home_path = "/Users/" + "alice" + "/project"
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "PII Test")
            git(repo, "config", "user.email", "pii@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "check_pii.sh"
            script.write_text(CHECK_PII_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            (repo / "README.md").write_text("safe\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "initial")

            (repo / "leak.txt").write_text(f"path={home_path}\n", encoding="utf-8")
            git(repo, "add", "leak.txt")
            git(repo, "commit", "-m", "add leak")

            result = subprocess.run(
                [str(script), "--tree", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("tree HEAD contains potential PII", result.stderr)
            self.assertIn(home_path, result.stderr)

    def test_tree_mode_allowlist_matches_content_not_location(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            home_path = "/Users/" + "alice" + "/project"
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "PII Test")
            git(repo, "config", "user.email", "pii@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "check_pii.sh"
            script.write_text(CHECK_PII_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            (repo / ".pii-allow").write_text(f"^path={home_path}$\n", encoding="utf-8")
            (repo / "leak.txt").write_text(f"path={home_path}\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "allow exact fixture line")

            allowed = subprocess.run(
                [str(script), "--tree", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

            (repo / ".pii-allow").write_text("leak.txt\n", encoding="utf-8")
            git(repo, "add", ".pii-allow")
            git(repo, "commit", "-m", "allow file path only")

            path_only = subprocess.run(
                [str(script), "--tree", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertEqual(path_only.returncode, 1)
            self.assertIn(home_path, path_only.stderr)

    def test_tree_mode_ignores_uncommitted_worktree_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            home_path = "/Users/" + "alice" + "/project"
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "PII Test")
            git(repo, "config", "user.email", "pii@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "check_pii.sh"
            script.write_text(CHECK_PII_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            (repo / "leak.txt").write_text(f"path={home_path}\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "commit leak without allowlist")

            (repo / ".pii-allow").write_text(f"^path={home_path}$\n", encoding="utf-8")

            result = subprocess.run(
                [str(script), "--tree", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(home_path, result.stderr)


if __name__ == "__main__":
    unittest.main()
