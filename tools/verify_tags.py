"""Confirm geh2026-prior-work exists on GitHub for every repo in prior-work-tags.txt and points at the logged commit."""
import subprocess
rows = [l.split() for l in open("prior-work-tags.txt", encoding="utf-8", errors="replace") if l.strip() and not l.startswith(("#", "REPO"))]
ok = 0
for repo, branch, sha, *_ in rows:
    out = subprocess.run(["git", "ls-remote", f"https://github.com/PollPower/{repo}.git", "refs/tags/geh2026-prior-work^{}"],
                         capture_output=True, text=True).stdout.split()
    remote = out[0] if out else "MISSING"
    match = remote == sha
    ok += match
    print(f"{repo:26} {'OK' if match else 'MISMATCH'}  {remote[:12]}")
print(f"{ok}/{len(rows)} tags verified on GitHub")
