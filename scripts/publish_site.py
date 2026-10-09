"""Publish a client's finished site to their own Cloudflare Pages, in one step.

    python scripts/publish_site.py --folder kerr-roofing --account <account id> --project kerr-roofing

Publishes outreach/sites/<folder>/site/ - ONLY the site subfolder, never the
folder around it (that holds their brief and the photos they uploaded). It
must contain index.html.

How the access works (docs/launching-a-client-site.md): the client's
Cloudflare account is theirs, and they invite you as an Administrator. One
API token of yours - Cloudflare > My Profile > API Tokens > Create Custom
Token with just Account > Cloudflare Pages > Edit, Account Resources: All
accounts, and no zone or DNS access - then publishes to every client you're
a member of. Save it as CLOUDFLARE_API_TOKEN in the panel's Settings.

Uses Cloudflare's own `wrangler` tool through npx, so Node.js must be
installed (nodejs.org, the LTS version). The first publish creates the Pages
project; add their domain afterwards in Cloudflare > Workers & Pages > the
project > Custom domains. The account id and project are remembered in
outreach/sites/<folder>/publish.json, so later publishes need only the folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACCOUNT = re.compile(r"^[0-9a-f]{32}$")
PROJECT = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?$")
FOLDER = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
WRANGLER = "wrangler@3"


def outreach_dir() -> Path:
    # Same rule as the other scripts: this checkout, or the main one when run from a worktree.
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


def site_dir(outreach: Path, folder: str) -> Path:
    """outreach/sites/<folder>/site, checked: a plain folder name, and an index.html inside."""
    if not FOLDER.match(folder):
        raise ValueError("The folder is the firm's folder name under outreach/sites, e.g. kerr-roofing.")
    base = outreach / "sites" / folder
    if not base.is_dir():
        raise ValueError(f"There's no outreach/sites/{folder} folder.")
    site = base / "site"
    if not (site / "index.html").is_file():
        raise ValueError(f"Put the finished site in outreach/sites/{folder}/site/ (with its index.html) - only that folder is published.")
    return site


def settings_for(outreach: Path, folder: str, account: str, project: str) -> tuple[str, str]:
    """The account id and project: as given, else as remembered from the last publish."""
    saved_path = outreach / "sites" / folder / "publish.json"
    saved = json.loads(saved_path.read_text(encoding="utf-8")) if saved_path.exists() else {}
    account = (account or saved.get("account") or "").strip().lower()
    project = (project or saved.get("project") or folder).strip().lower()
    if not ACCOUNT.match(account):
        raise ValueError("The Cloudflare account id is 32 letters and numbers - Cloudflare > the client's account > the right-hand side of Overview.")
    if not PROJECT.match(project):
        raise ValueError("The project name can use lowercase letters, numbers and hyphens (it becomes <name>.pages.dev).")
    saved_path.write_text(json.dumps({"account": account, "project": project}, indent=2), encoding="utf-8")
    return account, project


def npx() -> str | None:
    return shutil.which("npx.cmd" if sys.platform == "win32" else "npx") or shutil.which("npx")


def deploy_command(npx_path: str, site: Path, project: str, branch: str = "main") -> list[str]:
    return [npx_path, "--yes", WRANGLER, "pages", "deploy", str(site), "--project-name", project, "--branch", branch, "--commit-dirty=true"]


def create_command(npx_path: str, project: str) -> list[str]:
    return [npx_path, "--yes", WRANGLER, "pages", "project", "create", project, "--production-branch", "main"]


def missing_project(output: str) -> bool:
    return bool(re.search(r"project (?:was )?not found|could not find project|8000007", output, re.I))


def run(cmd: list[str], env: dict) -> tuple[int, str]:
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.strip())
    return proc.returncode, out


class PublishError(Exception):
    pass


def publish_live(outreach: Path, folder: str, token: str, runner=None) -> str:
    """Republishes an already-launched site, unattended (job_posts.py): the account and project saved by its
    first publish, the same QA gate -> its pages.dev address. PublishError says why not."""
    saved_path = outreach / "sites" / folder / "publish.json"
    if not saved_path.exists():
        raise PublishError("it hasn't been published from the panel yet")
    try:
        site = site_dir(outreach, folder)
        account, project = settings_for(outreach, folder, "", "")
    except ValueError as e:
        raise PublishError(str(e)) from e
    import site_qa

    problems, _ = site_qa.check(site, preview=False)
    if problems:
        raise PublishError(f"pre-launch QA found {len(problems)} problem(s), first: {problems[0]}")
    tool = npx()
    if not tool:
        raise PublishError("Node.js isn't installed (publishing needs it)")
    env = {**os.environ, "CLOUDFLARE_API_TOKEN": token, "CLOUDFLARE_ACCOUNT_ID": account, "WRANGLER_SEND_METRICS": "false", "CI": "1"}
    code, out = (runner or run)(deploy_command(tool, site, project), env)
    if code != 0:
        raise PublishError("Cloudflare refused: " + (out.strip().splitlines() or ["no message"])[-1][:200])
    return f"https://{project}.pages.dev"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--account", default="")
    ap.add_argument("--project", default="")
    ap.add_argument("--preview", action="store_true", help="a draft for the client to review, at preview.<project>.pages.dev - never the live site")
    args = ap.parse_args()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        sys.exit("Add CLOUDFLARE_API_TOKEN in Settings first (see the Publish card's note).")
    outreach = outreach_dir()
    try:
        site = site_dir(outreach, args.folder)
        account, project = settings_for(outreach, args.folder, args.account, args.project)
    except ValueError as e:
        sys.exit(str(e))
    import site_qa

    problems, warnings = site_qa.check(site, preview=args.preview)
    if problems:
        for line in problems:
            print(f"PROBLEM  {line}")
        sys.exit(f"Not published - pre-launch QA found {len(problems)} problem(s) above. Fix them, Build site, then publish.")
    print("Pre-launch QA passed" + (f" ({len(warnings)} warning(s) - press Check site to see them)." if warnings else "."), flush=True)
    tool = npx()
    if not tool:
        sys.exit("Publishing uses Cloudflare's wrangler tool, which needs Node.js - install the LTS version from nodejs.org, then restart the panel.")
    env = {**os.environ, "CLOUDFLARE_API_TOKEN": token, "CLOUDFLARE_ACCOUNT_ID": account, "WRANGLER_SEND_METRICS": "false", "CI": "1"}
    branch = "preview" if args.preview else "main"
    print(f"Publishing outreach/sites/{args.folder}/site to Cloudflare Pages project '{project}'"
          + (" as a PREVIEW for the client" if args.preview else "") + " ...", flush=True)
    code, out = run(deploy_command(tool, site, project, branch), env)
    if code != 0 and missing_project(out):
        print(f"First publish - creating the '{project}' project ...", flush=True)
        code, out = run(create_command(tool, project), env)
        if code == 0:
            code, out = run(deploy_command(tool, site, project, branch), env)
    if code != 0:
        sys.exit("Not published - see Cloudflare's message above. Usual causes: the token doesn't cover this account, or you're not yet a member of it.")
    if args.preview:
        print(f"\nREADY: preview at https://preview.{project}.pages.dev - send them that link. Hidden from Google; the live site is untouched.")
        print("With Draft build ticked, it has a Leave feedback button: each pin they drop lands in /admin and your inbox.")
        return
    print(f"\nREADY: live at https://{project}.pages.dev")
    print("First time? Add their domain: Cloudflare > Workers & Pages > the project > Custom domains (www and without). Then run the launch checks.")


if __name__ == "__main__":
    main()
