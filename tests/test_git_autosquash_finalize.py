from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FINALIZE_PATH = REPO_ROOT / "scripts" / "git_autosquash_finalize.sh"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


class GitAutosquashFinalizeTests(unittest.TestCase):
    def test_finalizer_squashes_fixups_runs_gates_and_force_pushes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            remote = root / "origin.git"
            repo = root / "repo"
            bin_dir = root / "bin"

            subprocess.run(["git", "init", "--bare", remote], check=True, capture_output=True)
            repo.mkdir()
            git(repo, "init", "--initial-branch=main")
            git(repo, "config", "user.name", "Finalize Test")
            git(repo, "config", "user.email", "finalize@example.invalid")

            scripts = repo / "scripts"
            scripts.mkdir()
            script = scripts / "git_autosquash_finalize.sh"
            script.write_text(FINALIZE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            gate_log = repo / "gate.log"
            for name in ("check_pii.sh", "check_layers.sh"):
                gate = scripts / name
                gate.write_text(f"#!/usr/bin/env sh\necho {name} >> gate.log\n", encoding="utf-8")
                gate.chmod(gate.stat().st_mode | stat.S_IXUSR)

            bin_dir.mkdir()
            cargo = bin_dir / "cargo"
            cargo.write_text(
                (
                    f"#!{sys.executable}\n"
                    "import pathlib, sys\n"
                    "pathlib.Path('gate.log').open('a', encoding='utf-8').write('cargo ' + ' '.join(sys.argv[1:]) + '\\n')\n"
                ),
                encoding="utf-8",
            )
            cargo.chmod(cargo.stat().st_mode | stat.S_IXUSR)

            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "initial")
            git(repo, "remote", "add", "origin", str(remote))
            git(repo, "push", "-u", "origin", "main")

            git(repo, "switch", "-c", "plan/finalize")
            (repo / "src.txt").write_text("implementation\n", encoding="utf-8")
            git(repo, "add", "src.txt")
            git(repo, "commit", "-m", "feat: Add implementation")
            impl_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()

            review = repo / "doc" / "reviews" / "review-00001.md"
            review.parent.mkdir(parents=True)
            review.write_text("# PR #1 - Finalize\n\n## Summary\n\nBody.\n", encoding="utf-8")
            git(repo, "add", "doc/reviews/review-00001.md")
            git(repo, "commit", "-m", "doc: Finalize plan and PR description")
            doc_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()

            (repo / "src.txt").write_text("implementation\nmechanical fix\n", encoding="utf-8")
            git(repo, "add", "src.txt")
            git(repo, "commit", f"--fixup={impl_sha}")

            with review.open("a", encoding="utf-8") as f:
                f.write("\n## Local review (2026-05-11)\n\nNo findings.\n")
            git(repo, "add", "doc/reviews/review-00001.md")
            git(repo, "commit", f"--fixup={doc_sha}")

            git(repo, "push", "-u", "origin", "plan/finalize")

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
            subprocess.run([str(script)], cwd=repo, env=env, check=True, capture_output=True, text=True)

            subjects = subprocess.check_output(
                ["git", "log", "--format=%s", "origin/main..origin/plan/finalize"],
                cwd=repo,
                text=True,
            ).splitlines()
            gates = gate_log.read_text(encoding="utf-8").splitlines()

            self.assertEqual(
                subjects,
                ["doc: Finalize plan and PR description", "feat: Add implementation"],
            )
            self.assertEqual(
                gates,
                [
                    "cargo fmt --all -- --check",
                    "check_pii.sh",
                    "check_layers.sh",
                    "cargo test --workspace",
                    "cargo clippy --all-targets -- -D warnings",
                ],
            )
            self.assertIn("mechanical fix", (repo / "src.txt").read_text(encoding="utf-8"))
            self.assertIn("## Local review", review.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
