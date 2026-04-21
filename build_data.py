import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CSV_FILE = Path("Most-Recent-Cohorts-Institution.csv")

CSV_COLUMNS = {
    "id": "UNITID",
    "name": "INSTNM",
    "city": "CITY",
    "state": "STABBR",
    "main": "MAIN",
    "control": "CONTROL",
    "preddeg": "PREDDEG",
    "enrollment": "UGDS",
    "sat": "SAT_AVG",
    "grad_rate": "C150_4",
    "pell_pct": "PCTPELL",
    "first_gen_pct": "PAR_ED_PCT_1STGEN",
    "hbcu": "HBCU",
    "hsi": "HSI",
}

PREDICTORS = ["median_sat", "pell_pct", "first_gen_pct"]


def parse_float(s):
    if s in ("", "NULL", "PrivacySuppressed", None):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def load_schools(csv_path):
    schools = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            main = parse_float(row.get(CSV_COLUMNS["main"]))
            control = parse_float(row.get(CSV_COLUMNS["control"]))
            preddeg = parse_float(row.get(CSV_COLUMNS["preddeg"]))
            enrollment = parse_float(row.get(CSV_COLUMNS["enrollment"]))

            if main != 1:
                continue
            if control not in (1, 2):
                continue
            if preddeg != 3:
                continue
            if enrollment is None or enrollment < 200:
                continue

            sat = parse_float(row.get(CSV_COLUMNS["sat"]))
            grad = parse_float(row.get(CSV_COLUMNS["grad_rate"]))
            pell = parse_float(row.get(CSV_COLUMNS["pell_pct"]))
            first_gen = parse_float(row.get(CSV_COLUMNS["first_gen_pct"]))

            if sat is None or grad is None or pell is None or first_gen is None:
                continue

            schools.append({
                "id": row[CSV_COLUMNS["id"]],
                "name": row[CSV_COLUMNS["name"]],
                "city": row[CSV_COLUMNS["city"]],
                "state": row[CSV_COLUMNS["state"]],
                "type": "Public" if control == 1 else "Private",
                "enrollment": int(enrollment),
                "median_sat": round(sat),
                "graduation_rate": round(grad * 100, 1),
                "pell_pct": round(pell * 100, 1),
                "first_gen_pct": round(first_gen * 100, 1),
                "hbcu": row.get(CSV_COLUMNS["hbcu"]) == "1",
                "hsi": row.get(CSV_COLUMNS["hsi"]) == "1",
            })

    return schools


def run_regression(schools):
    y = np.array([s["graduation_rate"] for s in schools])
    X = np.column_stack([
        [s["median_sat"] for s in schools],
        [s["pell_pct"] for s in schools],
        [s["first_gen_pct"] for s in schools],
        np.ones(len(schools)),
    ])

    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    predicted = X @ coeffs
    residuals = y - predicted

    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot

    n, k = X.shape
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k)

    for i, school in enumerate(schools):
        school["expected_graduation_rate"] = round(float(predicted[i]), 1)
        school["performance_score"] = round(float(residuals[i]), 1)

    schools.sort(key=lambda s: s["performance_score"], reverse=True)
    for i, school in enumerate(schools):
        school["rank"] = i + 1

    regression = {
        "predictors": PREDICTORS,
        "coefficients": {
            "sat": round(float(coeffs[0]), 4),
            "pell_pct": round(float(coeffs[1]), 4),
            "first_gen_pct": round(float(coeffs[2]), 4),
            "intercept": round(float(coeffs[3]), 2),
        },
        "r_squared": round(float(r_squared), 4),
        "adj_r_squared": round(float(adj_r_squared), 4),
        "n_schools": len(schools),
    }

    return schools, regression


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(CSV_FILE), help="Path to Scorecard institution CSV")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    print(f"Loading {csv_path}...")
    schools = load_schools(csv_path)
    print(f"  {len(schools)} schools after filtering")

    print("Running multiple regression: graduation_rate ~ SAT + PCTPELL + 1STGEN_PCT")
    schools, regression = run_regression(schools)
    c = regression["coefficients"]
    print(f"  R² = {regression['r_squared']}  (adjusted: {regression['adj_r_squared']})")
    print(f"  y = {c['sat']}*SAT + {c['pell_pct']}*Pell% + {c['first_gen_pct']}*1stGen% + {c['intercept']}")

    output = {
        "metadata": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "data_source": "U.S. Department of Education College Scorecard (Most Recent Cohorts, Institution-Level)",
            "regression": regression,
        },
        "schools": schools,
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(schools)} schools to data.json")
    print(f"\nTop 10:")
    for s in schools[:10]:
        flags = " ".join(f for f in (("HBCU" if s["hbcu"] else ""), ("HSI" if s["hsi"] else "")) if f)
        print(f"  {s['rank']:>3}. {s['name']:<48} SAT {s['median_sat']}  "
              f"Pell {s['pell_pct']}%  1stGen {s['first_gen_pct']}%  "
              f"Grad {s['graduation_rate']}%  Exp {s['expected_graduation_rate']}%  "
              f"Score {s['performance_score']:+.1f}  {flags}")


if __name__ == "__main__":
    main()
