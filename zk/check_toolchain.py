"""Report whether Midnight Compact (`compactc`) is on PATH.

Windows `compact.exe` is NTFS compression and must not be treated as the compiler.
"""
from __future__ import annotations

import shutil
import sys


def main() -> int:
    compactc = shutil.which("compactc")
    compact = shutil.which("compact")
    print(f"compactc: {compactc or 'NOT FOUND'}")
    print(f"compact:  {compact or 'NOT FOUND'}")
    if compact and compact.lower().endswith("system32\\compact.exe"):
        print("note: compact.exe is Windows NTFS compression, not Midnight Compact.")
    if not compactc:
        print("circuit NOT compiled. See zk/TEST_PLAN.md. Do not deploy.")
        return 1
    print("compactc is available; compile zk/record.compact locally. Do not deploy without asking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
