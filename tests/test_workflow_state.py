from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_STATE_PATH = REPO_ROOT / "scripts" / "workflow_state.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def run_state(repo: Path, script: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(path for path in ("/bin", "/usr/bin") if Path(path).exists())
    result = subprocess.run(
        [str(script)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return dict(line.split(": ", 1) for line in result.stdout.strip().splitlines())


class WorkflowStateTests(unittest.TestCase):
    def test_clean_pushed_branch_without_gh_reports_pushed_without_review_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            remote = root / "origin.git"
            repo = root / "repo"

            subprocess.run(["git", "init", "--bare", remote], check=True, capture_output=True)
            repo.mkdir()
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "Workflow Test")
            git(repo, "config", "user.email", "workflow@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir(parents=True)
            script = scripts / "workflow_state.sh"
            script.write_text(WORKFLOW_STATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            (repo / "README.md").write_text("seed\n", encoding="utf-8")

            git(repo, "add", ".")
            git(repo, "commit", "-m", "initial")
            git(repo, "remote", "add", "origin", str(remote))
            git(repo, "push", "-u", "origin", "main")

            branch = "flat-fallback"
            git(repo, "switch", "-c", branch)
            (repo / "README.md").write_text("branch work\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "feat: branch work")
            git(repo, "push", "-u", "origin", branch)

            fields = run_state(repo, script)
            self.assertEqual(fields["state"], "pushed")
            self.assertEqual(fields["origin_branch_ahead"], "0")
            self.assertEqual(fields["origin_branch_behind"], "0")
            self.assertEqual(fields["review_file"], "unknown")
            self.assertEqual(fields["local_review"], "unknown")


if __name__ == "__main__":
    unittest.main()
