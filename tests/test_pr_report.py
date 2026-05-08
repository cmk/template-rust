from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
PR_REPORT_PATH = SCRIPTS_DIR / "pr_report.py"

sys.path.insert(0, str(SCRIPTS_DIR))
spec = importlib.util.spec_from_file_location("pr_report", PR_REPORT_PATH)
assert spec is not None
pr_report = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = pr_report
spec.loader.exec_module(pr_report)


class PrReportTests(unittest.TestCase):
    def test_gh_api_rejects_non_list_json_for_list_endpoint(self) -> None:
        with (
            mock.patch.object(
                pr_report.subprocess,
                "check_output",
                return_value='{"message": "not found"}',
            ),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaises(SystemExit) as raised:
                pr_report.gh_api("repos/owner/repo/pulls/1/reviews")

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("expected list JSON", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
