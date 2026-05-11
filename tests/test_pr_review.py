from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PR_REVIEW_PATH = REPO_ROOT / "scripts" / "pr_review.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


class PrReviewTests(unittest.TestCase):
    def test_local_review_commits_review_artifact_as_doc_fixup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            remote = root / "origin.git"
            repo = root / "repo"
            bin_dir = root / "bin"

            subprocess.run(["git", "init", "--bare", remote], check=True, capture_output=True)
            repo.mkdir()
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "Review Test")
            git(repo, "config", "user.email", "review@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "pr_review.sh"
            script.write_text(PR_REVIEW_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            (scripts / "pr_report.py").write_text(
                "#!/usr/bin/env sh\nprintf 'doc/reviews/review-00002.md\\n'\n",
                encoding="utf-8",
            )
            (scripts / "pr_report.py").chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            (scripts / "git_squash.sh").write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
            (scripts / "git_squash.sh").chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            bin_dir.mkdir()
            codex = bin_dir / "codex"
            codex.write_text(
                (
                    f"#!{sys.executable}\n"
                    "import pathlib\n"
                    "print(f'No findings in {pathlib.Path.cwd() / \"scripts\" / \"pr_review.sh\"}.')\n"
                ),
                encoding="utf-8",
            )
            codex.chmod(codex.stat().st_mode | stat.S_IXUSR)
            gh = bin_dir / "gh"
            gh.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
            gh.chmod(gh.stat().st_mode | stat.S_IXUSR)

            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "initial")
            git(repo, "remote", "add", "origin", str(remote))
            git(repo, "push", "-u", "origin", "main")

            git(repo, "switch", "-c", "local-review")
            review_file = repo / "doc" / "reviews" / "review-00001.md"
            review_file.parent.mkdir(parents=True)
            review_file.write_text(
                "# PR #1 - Local review\n\n## Summary\n\nBody.\n",
                encoding="utf-8",
            )
            (repo / "README.md").write_text("branch\n", encoding="utf-8")
            git(repo, "add", "README.md", "doc/reviews/review-00001.md")
            git(repo, "commit", "-m", "doc: Finalize plan and PR description")
            doc_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
            subprocess.run([str(script)], cwd=repo, env=env, check=True, capture_output=True, text=True)

            subject = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=repo,
                text=True,
            ).strip()
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)

            self.assertEqual(subject, "fixup! doc: Finalize plan and PR description")
            self.assertEqual(status, "")
            target = subprocess.check_output(
                ["git", "rev-parse", "HEAD^"], cwd=repo, text=True
            ).strip()
            self.assertEqual(target, doc_sha)
            review_text = review_file.read_text(encoding="utf-8")
            self.assertIn("## Local review", review_text)
            self.assertIn("No findings in scripts/pr_review.sh.", review_text)
            self.assertNotIn(str(repo), review_text)

            subprocess.run([str(script)], cwd=repo, env=env, check=True, capture_output=True, text=True)
            subjects = subprocess.check_output(
                ["git", "log", "--format=%s", "-2"],
                cwd=repo,
                text=True,
            ).splitlines()
            self.assertEqual(
                subjects,
                [
                    "fixup! doc: Finalize plan and PR description",
                    "fixup! doc: Finalize plan and PR description",
                ],
            )


if __name__ == "__main__":
    unittest.main()
