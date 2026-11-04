"""Generate a SYNTHETIC sample dataset that mimics the layout of the
district-wise crime tables published by Kerala Police.

The numbers produced here are NOT real crime statistics. They exist only so the
pipeline and the Power BI dashboard can be built and demonstrated end to end.
Replace the files in data/raw/ with the official tables (see README) for any
real analysis.

The output deliberately reproduces the quirks of the source tables so the
cleaning step has something real to do:
  * one wide CSV per year (police districts as rows, crime heads as columns)
  * police-district splits such as "Thiruvananthapuram City" / "... Rural"
  * non-district rows (Railway Police, State total)
  * inconsistent header spelling and stray whitespace
  * a few blank cells
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw"
YEARS = range(2016, 2024)
SEED = 2024

# police district -> (revenue district, relative size weight)
POLICE_DISTRICTS = {
    "Thiruvananthapuram City": ("Thiruvananthapuram", 1.10),
    "Thiruvananthapuram Rural": ("Thiruvananthapuram", 1.00),
    "Kollam City": ("Kollam", 0.70),
    "Kollam Rural": ("Kollam", 0.85),
    "Pathanamthitta": ("Pathanamthitta", 0.65),
    "Alappuzha": ("Alappuzha", 1.05),
    "Kottayam": ("Kottayam", 0.95),
    "Idukki": ("Idukki", 0.70),
    "Kochi City": ("Ernakulam", 1.30),
    "Ernakulam Rural": ("Ernakulam", 1.05),
    "Thrissur City": ("Thrissur", 0.80),
    "Thrissur Rural": ("Thrissur", 0.85),
    "Palakkad": ("Palakkad", 1.00),
    "Malappuram": ("Malappuram", 1.25),
    "Kozhikode City": ("Kozhikode", 0.80),
    "Kozhikode Rural": ("Kozhikode", 0.75),
    "Wayanad": ("Wayanad", 0.45),
    "Kannur": ("Kannur", 1.05),
    "Kasaragod": ("Kasaragod", 0.60),
}

# crime head -> (base cases per unit weight in 2016, yearly growth, 2020 shock)
CRIME_HEADS = {
    "Murder": (18, 0.00, 0.95),
    "Attempt to Murder": (30, 0.02, 0.90),
    "Rape": (55, 0.04, 0.85),
    "Molestation": (125, 0.03, 0.80),
    "Cruelty by Husband/Relatives": (130, -0.01, 1.05),
    "Kidnapping & Abduction": (25, 0.03, 0.75),
    "Robbery": (35, -0.03, 0.70),
    "Burglary": (210, -0.04, 0.75),
    "Theft": (420, -0.02, 0.65),
    "Cheating": (190, 0.06, 0.95),
    "Riots": (110, -0.06, 0.55),
    "Hurt": (1150, -0.01, 0.80),
    "Cyber Crime": (12, 0.28, 1.15),
    "NDPS Act": (240, 0.17, 0.85),
    "Abkari Act": (520, -0.03, 1.10),
}

# Headers as they might appear across years (simulates inconsistent sources)
HEADER_VARIANTS = {
    "Kidnapping & Abduction": ["Kidnapping & Abduction", "Kidnapping and Abduction"],
    "Cruelty by Husband/Relatives": [
        "Cruelty by Husband/Relatives",
        "Cruelty by Husband or Relatives",
    ],
    "NDPS Act": ["NDPS Act", "N.D.P.S Act"],
    "Cyber Crime": ["Cyber Crime", "Cyber Crimes"],
}


def main() -> None:
    rng = random.Random(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Persistent district "personality" so patterns are stable across years
    district_bias = {
        (pd, head): rng.uniform(0.7, 1.35)
        for pd in POLICE_DISTRICTS
        for head in CRIME_HEADS
    }

    for year in YEARS:
        t = year - YEARS.start
        headers = [
            rng.choice(HEADER_VARIANTS.get(h, [h])) + (" " if rng.random() < 0.2 else "")
            for h in CRIME_HEADS
        ]
        rows = []
        totals = [0] * len(CRIME_HEADS)
        for pd, (_, weight) in POLICE_DISTRICTS.items():
            row = []
            for i, (head, (base, growth, shock)) in enumerate(CRIME_HEADS.items()):
                mean = base * weight * district_bias[(pd, head)] * (1 + growth) ** t
                if year == 2020:
                    mean *= shock
                value = max(0, round(rng.gauss(mean, mean * 0.08)))
                totals[i] += value
                row.append(value)
            if rng.random() < 0.03:  # occasional missing cell
                row[rng.randrange(len(row))] = ""
            name = pd.upper() if rng.random() < 0.1 else pd
            rows.append([f" {name}" if rng.random() < 0.1 else name, *row])

        railway = [max(0, round(v * 0.004)) for v in totals]
        rows.append(["Railway Police", *railway])
        rows.append(["State Total", *[a + b for a, b in zip(totals, railway)]])

        path = OUT_DIR / f"crime_{year}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Police District", *headers])
            writer.writerows(rows)
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
