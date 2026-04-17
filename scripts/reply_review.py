#!/usr/bin/env python3
"""Post a reply to a PR review comment thread on GitHub.

Wraps `gh api repos/{repo}/pulls/{pr}/comments/{id}/replies -f body=...`
so the agent doesn't have to remember the endpoint shape. Prints the
new comment's id and html_url on success.

Requires: `gh` CLI authenticated for the current repo.

Usage:
    scripts/reply_review.py <PR> <IN_REPLY_TO_ID> <BODY>
    scripts/reply_review.py <PR> <IN_REPLY_TO_ID> -    # read body from stdin
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


def gh_repo() -> str:
    try:
        return subprocess.check_output(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
    except FileNotFoundError:
        print("error: `gh` CLI not found; install GitHub CLI and ensure it is on PATH", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        msg = f": {detail}" if detail else ""
        print(f"error: failed to determine repository via `gh repo view`{msg}", file=sys.stderr)
        raise SystemExit(1)


def resolve_repo(pr: int, repo_override: str | None) -> str:
    """Pick the target repo, verifying the PR exists in it.

    If `--repo` was passed, trust it (explicit beats inferred).
    Otherwise auto-detect via `gh repo view` from cwd, then pre-flight
    `gh api repos/{repo}/pulls/{pr}`. On 404, error with both the
    detected repo and cwd so a user whose shell drifted into the wrong
    directory sees the mismatch immediately instead of getting an
    opaque 404 from the reply endpoint later.
    """
    if repo_override:
        return repo_override
    repo = gh_repo()
    try:
        subprocess.check_output(
            ["gh", "api", f"repos/{repo}/pulls/{pr}"],
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        print(
            "error: `gh` CLI not found; install GitHub CLI and ensure it is on PATH",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        if "Not Found" in detail or "404" in detail:
            cwd = os.getcwd()
            print(
                f"error: PR #{pr} not found in {repo} (repo detected from cwd: {cwd}).\n"
                f"  If the PR lives in a different repo, pass --repo owner/name.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        msg = f": {detail}" if detail else ""
        print(
            f"error: couldn't verify PR #{pr} in {repo} via `gh api`{msg}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return repo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pr", type=int, help="PR number")
    ap.add_argument(
        "in_reply_to_id",
        type=int,
        help="gh-id of the comment you are replying to",
    )
    ap.add_argument(
        "body",
        help="Reply body (markdown). Pass '-' to read from stdin.",
    )
    ap.add_argument("--repo", default=None, help="owner/name (default: auto)")
    args = ap.parse_args()

    body = sys.stdin.read() if args.body == "-" else args.body
    body = body.strip()
    if not body:
        print("error: empty body", file=sys.stderr)
        return 1

    repo = resolve_repo(args.pr, args.repo)
    path = f"repos/{repo}/pulls/{args.pr}/comments/{args.in_reply_to_id}/replies"

    try:
        result = subprocess.run(
            ["gh", "api", "--method", "POST", path, "-f", f"body={body}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print(
            "error: `gh` CLI not found; install GitHub CLI and ensure it is on PATH",
            file=sys.stderr,
        )
        return 1
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            sys.stderr.write(exc.stderr)
        return exc.returncode or 1

    data = json.loads(result.stdout)
    print(f"posted reply id={data['id']} url={data['html_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
