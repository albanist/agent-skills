#!/usr/bin/env python3
"""
What is about to be promoted, derived from git alone.

Used by the deploy-watch skill (step 1: scope, and after `verified` to place the bookmark), and
runnable on its own before any promotion.

A bookmark tag `<TAG_PREFIX><date>-<time>` marks the commit the environment is running. Everything
the branch has gained since is the scope of the next promotion. PRs are split into the ones that
change the site and the ones that only change the repo (CI, docs, tests, agent files), because only
the first group is what people mean by "what is being deployed".

    deploy-scope.py                   # scope since the latest bookmark
    deploy-scope.py --mark <sha>      # place a bookmark on <sha> and push it (after `verified`)
    deploy-scope.py --json            # machine-readable

Run it from the repository root. Adjust the settings below for your repository.
"""
import argparse, json, re, subprocess, sys
from datetime import datetime

# --- Settings -------------------------------------------------------------------------------
# The branch that gets promoted, as a remote ref.
BRANCH = "origin/main"
# Bookmark tags are TAG_PREFIX + date-time, e.g. deploy/live/2026-03-12-0915.
TAG_PREFIX = "deploy/live/"
# Paths that never change the built site. A PR touching only these is "repo-only".
REPO_ONLY = (
    r"^\.github/", r"^\.claude/", r"^\.agents/", r"^\.codex/", r"^docs/", r"^tests/", r"\.md$",
)
# Files whose change means new third-party package versions. Umbraco packages run their own
# database migrations on first boot, so these PRs are flagged for a look at the boot log.
PACKAGE_FILES = ("Directory.Packages.props", "packages.lock.json")
# Commit subjects to ignore, e.g. Umbraco Cloud's own back-pushes.
IGNORE_SUBJECTS = ("cloud changes since deployment",)
# ---------------------------------------------------------------------------------------------


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def latest_bookmark():
    # Newest by when the tag was created, not by the commit it points at: a rollback promotes an
    # older commit, and that tag must still win.
    out = git("for-each-ref", "--sort=-creatordate", "--format=%(refname:short)", f"refs/tags/{TAG_PREFIX}")
    return out.split()[0] if out.split() else None


def pr_title(number):
    """The PR title from GitHub for a bare merge commit; empty when gh is missing or fails."""
    try:
        return subprocess.run(["gh", "pr", "view", str(number), "--json", "title", "--jq", ".title"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def prs_since(bookmark):
    out = git("log", "--first-parent", "--format=%h%x09%ad%x09%s", "--date=short", f"{bookmark}..{BRANCH}")
    prs = []
    for line in out.splitlines():
        sha, day, subject = line.split("\t", 2)
        if any(s in subject.lower() for s in IGNORE_SUBJECTS):
            continue
        m = re.search(r"#(\d+)", subject)
        title = re.sub(r"^Merge pull request #\d+ from \S+\s*", "", subject)
        title = re.sub(r"\s*\(#\d+\)$", "", title)
        if m and not title.strip():
            title = pr_title(int(m.group(1))) or re.sub(r"^Merge pull request #\d+ from \S+/", "", subject)
        files = git("diff", "--name-only", f"{sha}^1", sha).split()
        site = [f for f in files if not any(re.search(p, f) for p in REPO_ONLY)]
        bump = any(f.endswith(p) for f in files for p in PACKAGE_FILES)
        prs.append({"sha": sha, "date": day, "pr": int(m.group(1)) if m else None, "title": title.strip(),
                    "site_effect": bool(site), "site_files": site, "package_bump": bump})
    return prs


def label(p):
    ref = f"#{p['pr']}" if p["pr"] else f"{p['sha']} (direct commit)"
    return ref + ("  [package versions changed: check migrations in the boot log]" if p["package_bump"] else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark", metavar="SHA", help="place a bookmark on SHA and push it")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.mark:
        # Date and time, so two promotions on one day get two bookmarks. Annotated, so the tag
        # records when the promotion happened independently of the commit it points at.
        tag = f"{TAG_PREFIX}{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        git("tag", "-a", "-m", f"Promoted {datetime.now():%Y-%m-%d %H:%M}", tag, a.mark)
        git("push", "origin", tag)
        print(f"bookmarked {tag} -> {a.mark}")
        return 0

    git("fetch", "-q", "origin", "--tags")
    bm = latest_bookmark()
    if not bm:
        print(f"no {TAG_PREFIX}* bookmark exists; place one with --mark <sha> for the commit the environment runs",
              file=sys.stderr)
        return 1
    prs = prs_since(bm)
    if a.json:
        print(json.dumps({"bookmark": bm, "prs": prs}, indent=2))
        return 0

    site = [p for p in prs if p["site_effect"]]
    repo = [p for p in prs if not p["site_effect"]]
    print(f"The environment is at {bm} ({git('rev-parse', '--short', bm + '^{commit}').strip()}). "
          f"Since then, {len(prs)} PR(s) merged to {BRANCH}.\n")
    print(f"Deploying to the site ({len(site)}):")
    for p in site:
        print(f"  {label(p)}  {p['title']}")
    print(f"\nRepo only, no site effect ({len(repo)}):")
    for p in repo:
        print(f"  {label(p)}  {p['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
