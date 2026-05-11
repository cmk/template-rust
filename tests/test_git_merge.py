from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_MERGE_PATH = REPO_ROOT / "scripts" / "git_merge.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


class GitMergeTests(unittest.TestCase):
    def test_merge_guard_rejects_remote_fixup_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            remote = root / "origin.git"
            repo = root / "repo"
            bin_dir = root / "bin"
            gh_log = root / "gh.log"

            subprocess.run(["git", "init", "--bare", remote], check=True, capture_output=True)
            repo.mkdir()
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "Merge Test")
            git(repo, "config", "user.email", "merge@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "git_merge.sh"
            script.write_text(GIT_MERGE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)

            bin_dir.mkdir()
            gh = bin_dir / "gh"
            gh.write_text(
                (
                    "#!/usr/bin/env sh\n"
                    f"echo \"$@\" >> {gh_log}\n"
                    "if [ \"$1 $2 $3\" = \"pr view 7\" ]; then\n"
                    "  printf 'feature\\n'\n"
                    "  exit 0\n"
                    "fi\n"
                    "if [ \"$1 $2\" = \"pr merge\" ]; then\n"
                    "  exit 0\n"
                    "fi\n"
                    "exit 1\n"
                ),
                encoding="utf-8",
            )
            gh.chmod(gh.stat().st_mode | stat.S_IXUSR)

            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "initial")
            git(repo, "remote", "add", "origin", str(remote))
            git(repo, "push", "-u", "origin", "main")

            git(repo, "switch", "-c", "feature")
            (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
            git(repo, "add", "feature.txt")
            git(repo, "commit", "-m", "feat: Add feature")
            target_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            (repo / "feature.txt").write_text("feature\nfixup\n", encoding="utf-8")
            git(repo, "add", "feature.txt")
            git(repo, "commit", f"--fixup={target_sha}")
            git(repo, "push", "-u", "origin", "feature")

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
            result = subprocess.run(
                [str(script), "7", "--squash"],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("still contains autosquashable commits", result.stderr)
            self.assertIn("scripts/git_autosquash_finalize.sh", result.stderr)
            self.assertNotIn("pr merge", gh_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
