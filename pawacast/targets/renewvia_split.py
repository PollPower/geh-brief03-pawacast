"""Pre-registered train/test split of the Renewvia sites (Zenodo 22149101), fixed on 28 Oct 2026
BEFORE any consumption value was read. Only site names and coordinates were used.

Neighbouring sites are grouped so a test site never has a near-twin in training:
  turkana_west   Kalobeyei Settlement, Kalobeyei Town, Kakuma 3 - Okapi  (all within ~25 km)
  cross_river    Balep, Bendeghe-Afi, Opu                                 (within ~5 km)
  bayelsa        Akipelai, Oloibiri, Emakalakala                          (within ~5 km)
  lake_victoria  Ndeda, Oyamo, Ringiti                                    (islands, within ~30 km)
  every other site is its own group.

Groups are assigned by a hash of the group name (no human choice): test if sha256(name) mod 3 == 0.
"""
import hashlib
import pandas as pd

GROUPS = {
    "Kalobeyei Settlement": "turkana_west", "Kalobeyei Town": "turkana_west", "Kakuma 3 - Okapi": "turkana_west",
    "Balep": "cross_river", "Bendeghe-Afi": "cross_river", "Opu": "cross_river",
    "Akipelai": "bayelsa", "Oloibiri": "bayelsa", "Emakalakala": "bayelsa",
    "Ndeda": "lake_victoria", "Oyamo": "lake_victoria", "Ringiti": "lake_victoria",
}

def group_of(project: str) -> str:
    return GROUPS.get(project, project.lower().replace(" ", "_"))

def role(group: str) -> str:
    return "test" if int(hashlib.sha256(group.encode()).hexdigest(), 16) % 3 == 0 else "train"

def split(projects: pd.DataFrame) -> pd.DataFrame:
    d = projects[["projectName", "country", "lat", "long", "powerOnDate"]].copy()
    d["group"] = d.projectName.map(group_of)
    d["role"] = d.group.map(role)
    return d.sort_values(["role", "group", "projectName"]).reset_index(drop=True)

if __name__ == "__main__":
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw" / "renewvia" / "minigridprojects.parquet"
    s = split(pd.read_parquet(p))
    out = pathlib.Path(__file__).resolve().parent / "renewvia_split.csv"
    s.to_csv(out, index=False)
    print(s.to_string(index=False))
    print(s.groupby("role").agg(sites=("projectName", "count"), groups=("group", "nunique"),
                                kenya=("country", lambda c: (c == "Kenya").sum())))
