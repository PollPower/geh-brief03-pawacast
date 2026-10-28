import json, os, re, sys, glob
ROOT = r"C:\Users\Garrett\Projects"
REPOS = ["contracts", "pp-settle-service", "consumer-standalone", "producer-standalone",
         "pollpower-node-firmware", "solar-scouting", "settlement-api", "meter-authority-service",
         "pollpower-v2-api", "pollpower-br-firmware", "pollpower-sfn-firmware", "pollpower-ops-dashboard"]
SKIP = {"node_modules", ".git", "dist", "build", ".expo", "venv", ".venv", "android", "ios"}
out = {}

def lic_from_nm(repo_dir, name):
    for base in [repo_dir] + [os.path.dirname(p) for p in glob.glob(os.path.join(repo_dir, "*", "package.json"))]:
        pj = os.path.join(base, "node_modules", *name.split("/"), "package.json")
        if os.path.exists(pj):
            try:
                d = json.load(open(pj, encoding="utf-8"))
                l = d.get("license")
                if isinstance(l, dict): l = l.get("type")
                return l or "", d.get("version", "")
            except Exception:
                pass
    return "", ""

for r in REPOS:
    rd = os.path.join(ROOT, r)
    if not os.path.isdir(rd):
        out[r] = {"missing": True}; continue
    deps = {}
    files = []
    for dp, dns, fns in os.walk(rd):
        dns[:] = [d for d in dns if d not in SKIP]
        for f in fns:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, rd)
            if f == "package.json":
                files.append(rel)
                try:
                    d = json.load(open(p, encoding="utf-8"))
                except Exception:
                    continue
                for sec in ("dependencies", "devDependencies", "peerDependencies"):
                    for n, v in (d.get(sec) or {}).items():
                        lic, ver = lic_from_nm(rd, n)
                        deps.setdefault(("npm", n), {"spec": v, "lic": lic, "ver": ver, "dev": sec != "dependencies"})
            elif f in ("requirements.txt",) or (f.startswith("requirements") and f.endswith(".txt")):
                files.append(rel)
                for line in open(p, encoding="utf-8", errors="ignore"):
                    line = line.split("#")[0].strip()
                    if not line or line.startswith("-"): continue
                    n = re.split(r"[<>=!~\[; ]", line)[0]
                    deps.setdefault(("pypi", n), {"spec": line[len(n):], "lic": "", "ver": "", "dev": False})
            elif f == "pyproject.toml":
                files.append(rel)
                txt = open(p, encoding="utf-8", errors="ignore").read()
                m = re.search(r"dependencies\s*=\s*\[(.*?)\]", txt, re.S)
                if m:
                    for s in re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)):
                        n = re.split(r"[<>=!~\[; ]", s)[0]
                        deps.setdefault(("pypi", n), {"spec": s[len(n):], "lic": "", "ver": "", "dev": False})
            elif f in ("Cargo.toml", "go.mod", "platformio.ini", "CMakeLists.txt", "west.yml", "idf_component.yml", "manifest.yml"):
                files.append(rel)
            elif f.endswith(".slcp") or f.endswith(".syscfg") or f == "makefile" or f == "Makefile":
                files.append(rel)
    out[r] = {"files": files[:40], "deps": [[k[0], k[1], v["spec"], v["ver"], v["lic"], v["dev"]] for k, v in sorted(deps.items())]}

json.dump(out, open(os.path.join(ROOT, "geh-brief03-pawacast", "deps.json"), "w"), indent=1)
for r, v in out.items():
    print(r, "MISSING" if v.get("missing") else f"{len(v['deps'])} deps, manifests: {v['files'][:8]}")
