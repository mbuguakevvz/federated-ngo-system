# ================================================================
# ETL Pipeline — Chapter Nodes → Central Warehouse
# Federated NGO Data System
# Extract → Transform → Load (Star Schema)
# ================================================================

import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime, date

# ── Paths ────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
NODES_DIR     = BASE_DIR / "chapter_nodes"
WAREHOUSE_DIR = BASE_DIR / "warehouse"
WAREHOUSE_DB  = WAREHOUSE_DIR / "ngo_warehouse.duckdb"
SCHEMA_FILE   = WAREHOUSE_DIR / "warehouse_schema.sql"

CHAPTER_NODES = {
    "nairobi": NODES_DIR / "nairobi.duckdb",
    "kisumu":  NODES_DIR / "kisumu.duckdb",
    "mombasa": NODES_DIR / "mombasa.duckdb",
}

# ── Helpers ──────────────────────────────────────────────────
def get_warehouse():
    wh = duckdb.connect(str(WAREHOUSE_DB))
    wh.execute(SCHEMA_FILE.read_text())
    return wh

def log_audit(wh, log_id, chapter, table, rows, status, notes=""):
    wh.execute("""
        INSERT INTO etl_audit_log
            (log_id, run_timestamp, chapter, table_name, rows_loaded, status, notes)
        VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
    """, [log_id, chapter, table, rows, status, notes])
    print(f"   [{status}] {chapter}.{table} — {rows} rows")

def age_group(dob):
    if dob is None:
        return "Unknown"
    today = date.today()
    age   = today.year - dob.year
    if age < 18:  return "Child (0-17)"
    if age < 36:  return "Youth (18-35)"
    if age < 60:  return "Adult (36-59)"
    return "Elderly (60+)"

def date_key(d):
    return int(d.strftime("%Y%m%d")) if d else None

# ── Date dimension ───────────────────────────────────────────
def load_dim_date(wh):
    print("\n  Loading dim_date ...")
    dates = pd.date_range("2020-01-01", "2025-12-31", freq="D")
    rows  = []
    for d in dates:
        rows.append({
            "date_key":    int(d.strftime("%Y%m%d")),
            "full_date":   d.date(),
            "year":        d.year,
            "quarter":     d.quarter,
            "month":       d.month,
            "month_name":  d.strftime("%B"),
            "week":        int(d.strftime("%W")),
            "day_of_week": d.strftime("%A"),
        })
    df = pd.DataFrame(rows)
    wh.execute("DELETE FROM dim_date")
    wh.register("dim_date_df", df)
    wh.execute("INSERT INTO dim_date SELECT * FROM dim_date_df")
    print(f"     {len(df)} date records loaded.")

# ── Extract from one chapter node ───────────────────────────
def extract(chapter, table):
    path = CHAPTER_NODES[chapter]
    con  = duckdb.connect(str(path), read_only=True)
    df   = con.execute(f"SELECT * FROM {table}").df()
    con.close()
    return df

# ── Transform & Load: dim_chapter ───────────────────────────
def load_dim_chapter(wh, audit_start):
    print("\n  Loading dim_chapter ...")
    wh.execute("DELETE FROM dim_chapter")
    key = 1
    for i, (chapter, _) in enumerate(CHAPTER_NODES.items()):
        df = extract(chapter, "chapters")
        for _, row in df.iterrows():
            wh.execute("""
                INSERT INTO dim_chapter
                    (chapter_key, chapter_id, chapter_name, region, county, is_hq, source_node)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [key, int(row.chapter_id), row.chapter_name,
                  row.region, row.county, bool(row.is_hq), chapter])
            key += 1
        log_audit(wh, audit_start + i, chapter, "dim_chapter", len(df), "SUCCESS")

# ── Transform & Load: dim_beneficiary ───────────────────────
def load_dim_beneficiary(wh, audit_start):
    print("\n  Loading dim_beneficiary ...")
    wh.execute("DELETE FROM dim_beneficiary")
    key = 1
    for i, chapter in enumerate(CHAPTER_NODES):
        df = extract(chapter, "beneficiaries")
        for _, row in df.iterrows():
            dob = row.date_of_birth
            if hasattr(dob, "date"):
                dob = dob.date()
            wh.execute("""
                INSERT INTO dim_beneficiary
                    (beneficiary_key, beneficiary_id, full_name, gender,
                     date_of_birth, age_group, county, sub_county, source_node)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [key, int(row.beneficiary_id), row.full_name, row.gender,
                  dob, age_group(dob), row.county, row.sub_county, chapter])
            key += 1
        log_audit(wh, audit_start + i, chapter, "dim_beneficiary", len(df), "SUCCESS")

# ── Transform & Load: dim_project ───────────────────────────
def load_dim_project(wh, audit_start):
    print("\n  Loading dim_project ...")
    wh.execute("DELETE FROM dim_project")
    key = 1
    for i, chapter in enumerate(CHAPTER_NODES):
        df = extract(chapter, "projects")
        for _, row in df.iterrows():
            wh.execute("""
                INSERT INTO dim_project
                    (project_key, project_id, project_name, thematic_area,
                     status, start_date, end_date, budget_ksh, source_node)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [key, int(row.project_id), row.project_name, row.thematic_area,
                  row.status, row.start_date, row.end_date,
                  float(row.budget_ksh), chapter])
            key += 1
        log_audit(wh, audit_start + i, chapter, "dim_project", len(df), "SUCCESS")

# ── Transform & Load: fact_services ─────────────────────────
def load_fact_services(wh, audit_start):
    print("\n  Loading fact_services ...")
    wh.execute("DELETE FROM fact_services")

    # Build lookup maps
    ben_map  = {(r.beneficiary_id, r.source_node): r.beneficiary_key
                for r in wh.execute("SELECT * FROM dim_beneficiary").df().itertuples()}
    proj_map = {(r.project_id, r.source_node): r.project_key
                for r in wh.execute("SELECT * FROM dim_project").df().itertuples()}
    chap_map = {r.source_node: r.chapter_key
                for r in wh.execute("SELECT * FROM dim_chapter").df().itertuples()}

    key = 1
    for i, chapter in enumerate(CHAPTER_NODES):
        df = extract(chapter, "services")
        loaded = 0
        for _, row in df.iterrows():
            bkey = ben_map.get((int(row.beneficiary_id), chapter))
            pkey = proj_map.get((int(row.project_id), chapter))
            ckey = chap_map.get(chapter)
            sdate = row.service_date
            if hasattr(sdate, "date"):
                sdate = sdate.date()
            dkey = date_key(sdate)
            if not all([bkey, pkey, ckey, dkey]):
                continue
            wh.execute("""
                INSERT INTO fact_services
                    (service_key, service_id, beneficiary_key, project_key,
                     chapter_key, date_key, service_type, location, source_node)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [key, int(row.service_id), bkey, pkey, ckey, dkey,
                  row.service_type, row.location, chapter])
            key += 1
            loaded += 1
        log_audit(wh, audit_start + i, chapter, "fact_services", loaded, "SUCCESS")

# ── Transform & Load: fact_funds ────────────────────────────
def load_fact_funds(wh, audit_start):
    print("\n  Loading fact_funds ...")
    wh.execute("DELETE FROM fact_funds")

    proj_map = {(r.project_id, r.source_node): r.project_key
                for r in wh.execute("SELECT * FROM dim_project").df().itertuples()}
    chap_map = {r.source_node: r.chapter_key
                for r in wh.execute("SELECT * FROM dim_chapter").df().itertuples()}

    key = 1
    for i, chapter in enumerate(CHAPTER_NODES):
        df = extract(chapter, "funds")
        loaded = 0
        for _, row in df.iterrows():
            pkey = proj_map.get((int(row.project_id), chapter))
            ckey = chap_map.get(chapter)
            rdate = row.received_on
            if hasattr(rdate, "date"):
                rdate = rdate.date()
            dkey = date_key(rdate)
            if not all([pkey, ckey, dkey]):
                continue
            wh.execute("""
                INSERT INTO fact_funds
                    (fund_key, fund_id, project_key, chapter_key, date_key,
                     donor_name, fund_type, amount_ksh, source_node)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [key, int(row.fund_id), pkey, ckey, dkey,
                  row.donor_name, row.fund_type, float(row.amount_ksh), chapter])
            key += 1
            loaded += 1
        log_audit(wh, audit_start + i, chapter, "fact_funds", loaded, "SUCCESS")


# ── Main ETL Runner ──────────────────────────────────────────
def run_etl():
    print("=" * 55)
    print("  NGO Federated Data System — ETL Pipeline")
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    wh = get_warehouse()

    load_dim_date(wh)
    load_dim_chapter(wh,     audit_start=100)
    load_dim_beneficiary(wh, audit_start=200)
    load_dim_project(wh,     audit_start=300)
    load_fact_services(wh,   audit_start=400)
    load_fact_funds(wh,      audit_start=500)

    # Summary
    print("\n" + "=" * 55)
    print("  WAREHOUSE SUMMARY")
    print("=" * 55)
    for table in ["dim_chapter","dim_beneficiary","dim_project",
                  "dim_date","fact_services","fact_funds"]:
        count = wh.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   {table:<25} {count:>6} rows")

    wh.close()
    print("\n  ETL complete. Warehouse ready.")

if __name__ == "__main__":
    run_etl()