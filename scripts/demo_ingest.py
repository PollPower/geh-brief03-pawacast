"""DEMO: Maji Moto prior + growth shifted by Olkiramatian-area shared records.

Same function the Streamlit app calls (`maji_moto_sharing_demo`). Does not
refit frozen β. Labelled DEMO.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pawacast.sharing.ingest import maji_moto_sharing_demo

OUT = ROOT / "results" / "sharing_ingest_demo.json"


def main() -> None:
    demo = maji_moto_sharing_demo()
    OUT.write_text(
        json.dumps(demo, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(demo["headline"], flush=True)
    print(json.dumps(demo, indent=2), flush=True)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
