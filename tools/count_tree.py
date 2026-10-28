import os, json, re, collections
ROOT = r"C:\Users\Garrett\Projects"
REPOS = ["contracts\\tariff-registry", "consumer-standalone", "producer-standalone", "settlement-api",
         "meter-authority-service", "pollpower-v2-api", "pollpower-ops-dashboard"]
allpk = {}
for r in REPOS:
    nm = os.path.join(ROOT, r, "node_modules")
    n = 0
    if not os.path.isdir(nm):
        print(r, "no node_modules"); continue
    for dp, dns, fns in os.walk(nm):
        if "package.json" in fns and os.path.basename(os.path.dirname(dp)) in ("node_modules",) or (
            "package.json" in fns and os.path.basename(os.path.dirname(os.path.dirname(dp))) == "node_modules" and os.path.basename(os.path.dirname(dp)).startswith("@")):
            try:
                d = json.load(open(os.path.join(dp, "package.json"), encoding="utf-8"))
                l = d.get("license")
                if isinstance(l, dict): l = l.get("type")
                if isinstance(l, list): l = " OR ".join(x.get("type", "") for x in l)
                if d.get("name"):
                    allpk[(d["name"], d.get("version", ""))] = l or "UNKNOWN"; n += 1
            except Exception:
                pass
    print(r, n, "installed packages")
print("UNIQUE name@version across repos:", len(allpk))
print("UNIQUE names:", len({k[0] for k in allpk}))
c = collections.Counter(allpk.values())
print("LICENCES:", c.most_common(25))
json.dump([[k[0], k[1], v] for k, v in sorted(allpk.items())], open(os.path.join(ROOT, "geh-brief03-pawacast", "npm_tree.json"), "w"))
# firmware SDKs
for f in [r"pollpower-node-firmware\freertos\ticlang\makefile", r"pollpower-br-firmware\freertos\ticlang\makefile"]:
    p = os.path.join(ROOT, f)
    t = open(p, errors="ignore").read()
    print(f, set(re.findall(r"simplelink_[a-z0-9_]+sdk_[0-9_]+", t))[:5] if False else sorted(set(re.findall(r"simplelink_[a-z0-9_]+?sdk_[0-9_]+", t)))[:5])
for f in [r"pollpower-sfn-firmware\CMakeLists.txt", r"pollpower-sfn-firmware\main\CMakeLists.txt"]:
    print(f, open(os.path.join(ROOT, f), errors="ignore").read()[:600])
for d in ["pollpower-sfn-firmware", "pollpower-node-firmware"]:
    for fn in ["dependencies.lock", "sdkconfig", "README.md"]:
        p = os.path.join(ROOT, d, fn)
        if os.path.exists(p):
            t = open(p, errors="ignore").read()
            m = re.findall(r"(?i)(esp-idf[^\n]{0,60}|IDF_VERSION[^\n]{0,40}|SimpleLink[^\n]{0,80}|FreeRTOS[^\n]{0,60}|Wi-SUN[^\n]{0,60})", t)
            print(d, fn, m[:6])
