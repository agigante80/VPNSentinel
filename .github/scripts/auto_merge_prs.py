#!/usr/bin/env python3
"""Auto-merge watcher for PRs targeting refactor/unified-architecture.

Requirements:
- Set environment variable GITHUB_TOKEN with a token that has repo access.

This script polls GitHub every 180 seconds, lists open PRs with base
`refactor/unified-architecture`, and attempts to merge any PR whose
check runs and combined status are green. Actions are logged to
.github/auto_merge.log.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from http.client import HTTPConnection
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


SLEEP = int(os.getenv("AUTO_MERGE_POLL_SECS", "180"))
BASE = "refactor/unified-architecture"
LOG = os.path.join(os.path.dirname(__file__), "../auto_merge.log")


def log(msg: str) -> None:
    ts = datetime.utcnow().isoformat() + "Z"
    line = f"{ts} {msg}\n"
    with open(LOG, "a") as f:
        f.write(line)
    print(line, end="")


def get_repo() -> str:
    # Try to derive origin repo from git config
    try:
        import subprocess

        out = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
        m = re.search(r"[:/](?P<owner>[^/]+)/(?P<repo>[^/]+)(?:\.git)?$", out)
        if m:
            owner = m.group('owner')
            repo = m.group('repo')
            # strip trailing .git if present (defensive)
            if repo.endswith('.git'):
                repo = repo[:-4]
            return f"{owner}/{repo}"
    except Exception:
        pass
    # Fallback: require env var
    repo = os.getenv("GITHUB_REPO")
    if not repo:
        raise SystemExit("GITHUB_REPO not set and could not detect repo from git remote")
    return repo


def gh_api(path: str, method: str = "GET", data: bytes | None = None):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN environment variable is required")

    url = f"https://api.github.com{path}"
    req = Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "auto-merge-watcher")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        if e.code == 401:
            log(f"HTTPError 401 Unauthorized for {path}; check GITHUB_TOKEN scopes and validity. Response body: {body}")
            raise
        log(f"HTTPError {e.code} {path} body={body}")
        raise
    except URLError as e:
        log(f"URLError {e} for {path}")
        raise


def pr_list(repo: str):
    path = f"/repos/{repo}/pulls?state=open&base={BASE}"
    return gh_api(path)


def get_check_runs(repo: str, sha: str):
    path = f"/repos/{repo}/commits/{sha}/check-runs"
    data = gh_api(path)
    return data.get("check_runs", [])


def get_combined_status(repo: str, sha: str):
    path = f"/repos/{repo}/commits/{sha}/status"
    return gh_api(path)


def is_checks_green(repo: str, sha: str) -> bool:
    try:
        status = get_combined_status(repo, sha)
        state = status.get("state")
        if state != "success":
            return False
        runs = get_check_runs(repo, sha)
        # Accept check runs that are success, skipped, or neutral
        for r in runs:
            conclusion = r.get("conclusion")
            status_val = r.get("status")
            if status_val == "in_progress" or (conclusion not in ("success", "skipped", "neutral", None)):
                return False
        return True
    except Exception:
        return False


def attempt_merge(repo: str, pr_number: int) -> bool:
    path = f"/repos/{repo}/pulls/{pr_number}/merge"
    payload = json.dumps({"merge_method": "merge"}).encode("utf-8")
    try:
        res = gh_api(path, method="PUT", data=payload)
        merged = res.get("merged", False)
        return merged
    except Exception:
        return False


def main():
    repo = get_repo()
    log(f"Starting auto-merge watcher for repo={repo}, base={BASE}, poll={SLEEP}s")
    while True:
        try:
            prs = pr_list(repo)
            if not prs:
                log("No open PRs targeting base")
            for pr in prs:
                number = pr.get("number")
                title = pr.get("title")
                head = pr.get("head", {})
                sha = head.get("sha")
                user = pr.get("user", {}).get("login")
                log(f"Checking PR #{number} '{title}' from {user} (sha={sha})")
                if not sha:
                    log(f"PR #{number} has no head sha, skipping")
                    continue
                if is_checks_green(repo, sha):
                    log(f"Checks green for PR #{number}, attempting merge")
                    ok = attempt_merge(repo, number)
                    if ok:
                        log(f"Successfully merged PR #{number}")
                    else:
                        log(f"Failed to merge PR #{number}")
                else:
                    log(f"Checks not green for PR #{number}, skipping")
        except Exception as e:
            log(f"Error during poll loop: {e}")
        time.sleep(SLEEP)


if __name__ == "__main__":
    main()
