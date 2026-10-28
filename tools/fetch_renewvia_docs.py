"""Clone Renewvia's dataset documentation repo (data dictionary + example scripts) into data/raw/renewvia_docs/ (git-ignored)."""
import pathlib, subprocess
dest = pathlib.Path("data/raw/renewvia_docs")
if not dest.exists():
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Renewvia-Energy/minigrid-dataset.git", str(dest)], check=True)
for p in sorted(dest.rglob("*")):
    if ".git" in p.parts:
        continue
    if p.is_file():
        print(f"{p.relative_to(dest)}  ({p.stat().st_size // 1024} KB)")
lic = [p for p in dest.iterdir() if p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))]
print("LICENCE FILES:", [p.name for p in lic] or "none")
