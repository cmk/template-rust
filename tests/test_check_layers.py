from __future__ import annotations

import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_LAYERS_PATH = REPO_ROOT / "scripts" / "check_layers.sh"


class CheckLayersTests(unittest.TestCase):
    def test_multiline_grouped_import_collects_until_semicolon(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True)

            script = repo / "scripts" / "check_layers.sh"
            script.parent.mkdir()
            script.write_text(CHECK_LAYERS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)

            core = repo / "crates" / "core" / "src"
            cli = repo / "crates" / "cli" / "src"
            core.mkdir(parents=True)
            cli.mkdir(parents=True)
            (core / "conn.rs").write_text(
                "\n".join(
                    [
                        "//! layer: conn",
                        "//! depends-on:",
                        "use crate::{",
                        "    // the semicolon in this comment; is not the group terminator",
                        "    /* this block comment; is not the group terminator either */",
                        "    helper::{self, value},",
                        "    test,",
                        "};",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (core / "test.rs").write_text(
                "//! layer: test\n//! depends-on: conn\n",
                encoding="utf-8",
            )
            (cli / "command.rs").write_text(
                "//! layer: command\n//! depends-on: parse\n",
                encoding="utf-8",
            )
            (cli / "parse.rs").write_text(
                "//! layer: parse\n//! depends-on:\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [str(script)],
                cwd=repo,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("imports test", result.stderr)


if __name__ == "__main__":
    unittest.main()
