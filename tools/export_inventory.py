import json, os, csv
H = r"C:\Users\Garrett\Projects\geh-brief03-pawacast"
os.makedirs(os.path.join(H, "oss-inventory"), exist_ok=True)
tree = json.load(open(os.path.join(H, "npm_tree.json")))
with open(os.path.join(H, "oss-inventory", "npm-full-tree.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["package", "version", "license"]); w.writerows(tree)
deps = json.load(open(os.path.join(H, "deps.json")))
rows = []
for repo, v in deps.items():
    for eco, name, spec, ver, lic, dev in v.get("deps", []):
        if eco == "pypi" and (not name or not name[0].isalpha() or name in ("emscripten", "win32", "locust")):
            continue
        rows.append([repo, eco, name, ver or spec, lic, "dev" if dev else "runtime"])
with open(os.path.join(H, "oss-inventory", "direct-dependencies.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["repo", "ecosystem", "package", "version", "license", "scope"]); w.writerows(rows)
for r in rows:
    if r[0] in ("producer-standalone",): continue
    print("\t".join(r))
