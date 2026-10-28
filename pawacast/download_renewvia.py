"""Download the Renewvia operational dataset (Zenodo 22149101, CC BY-SA 4.0) into data/raw/renewvia/.

  python -m pawacast.download_renewvia meta     # small tables only (projects, customers, tariffs, ...)
  python -m pawacast.download_renewvia clean    # + gap-filled 15-min consumption per site (~9.6 GB)

Raw 'sparkmeterreadings_<site>' files (~65 GB) are not downloaded; the 'clean' derived product is used.
"""
import pathlib, sys, requests

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw" / "renewvia"
RECORD = 22149101

def files():
    j = requests.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60).json()
    return [(f["key"], f["size"], f["links"]["self"]) for f in j["files"]]

def fetch(url, dest, size):
    if dest.exists() and dest.stat().st_size == size:
        print("have", dest.name); return
    print(f"get  {dest.name} ({size / 1e6:.0f} MB)", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 22):
                f.write(chunk)
    tmp.replace(dest)

def main(mode="meta"):
    RAW.mkdir(parents=True, exist_ok=True)
    for key, size, url in sorted(files(), key=lambda f: f[1]):
        is_meta = not key.startswith("sparkmeterreadings_")
        is_clean = key.startswith("sparkmeterreadings_clean_")
        if is_meta or (mode == "clean" and is_clean):
            fetch(url, RAW / key, size)

if __name__ == "__main__":
    main(*sys.argv[1:])
