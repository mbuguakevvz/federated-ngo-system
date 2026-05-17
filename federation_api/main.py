# ================================================================
# Federated NGO Data System — Federation API
# Queries all chapter DuckDB nodes and merges results
# ================================================================

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import duckdb
import pandas as pd
from typing import Optional
from datetime import date

app = FastAPI(
    title="Federated NGO Data API",
    description="Cross-chapter data federation layer for a chaptered NGO operating in Kenya.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Chapter node paths ────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
NODES_DIR  = BASE_DIR / "chapter_nodes"

CHAPTER_NODES = {
    "nairobi": NODES_DIR / "nairobi.duckdb",
    "kisumu":  NODES_DIR / "kisumu.duckdb",
    "mombasa": NODES_DIR / "mombasa.duckdb",
}

# ── Helper: query one chapter node ───────────────────────────
def query_node(chapter: str, sql: str, params: list = []) -> pd.DataFrame:
    path = CHAPTER_NODES.get(chapter)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail=f"Chapter node '{chapter}' not found.")
    con = duckdb.connect(str(path), read_only=True)
    df  = con.execute(sql, params).df()
    con.close()
    df["chapter"] = chapter
    return df

# ── Helper: fan out query to ALL chapters ────────────────────
def query_all_nodes(sql: str, params: list = []) -> pd.DataFrame:
    frames = []
    for chapter in CHAPTER_NODES:
        try:
            frames.append(query_node(chapter, sql, params))
        except Exception as e:
            print(f"Warning: could not query {chapter}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    return {
        "system": "Federated NGO Data System",
        "version": "1.0.0",
        "chapters": list(CHAPTER_NODES.keys()),
        "status": "online"
    }

@app.get("/health", tags=["Health"])
def health_check():
    status = {}
    for chapter, path in CHAPTER_NODES.items():
        try:
            con = duckdb.connect(str(path), read_only=True)
            con.execute("SELECT 1").fetchone()
            con.close()
            status[chapter] = "healthy"
        except:
            status[chapter] = "unreachable"
    return {"nodes": status}


# ── Beneficiaries ────────────────────────────────────────────

@app.get("/beneficiaries", tags=["Beneficiaries"])
def get_all_beneficiaries(
    chapter: Optional[str] = Query(None, description="Filter by chapter: nairobi, kisumu, mombasa"),
    gender:  Optional[str] = Query(None, description="Filter by gender: Male or Female"),
    county:  Optional[str] = Query(None, description="Filter by county name"),
    limit:   int           = Query(100, le=1000)
):
    sql = "SELECT * FROM beneficiaries WHERE is_active = TRUE"
    if gender:
        sql += f" AND gender = '{gender}'"
    if county:
        sql += f" AND county ILIKE '%{county}%'"
    sql += f" LIMIT {limit}"

    if chapter:
        df = query_node(chapter, sql)
    else:
        df = query_all_nodes(sql)

    return {
        "total": len(df),
        "filters": {"chapter": chapter, "gender": gender, "county": county},
        "data": df.to_dict(orient="records")
    }

@app.get("/beneficiaries/count", tags=["Beneficiaries"])
def count_beneficiaries_by_chapter():
    sql = "SELECT COUNT(*) as total, gender, county FROM beneficiaries GROUP BY gender, county"
    df  = query_all_nodes(sql)
    summary = df.groupby("chapter")["total"].sum().reset_index()
    return {
        "total_across_all_chapters": int(df["total"].sum()),
        "by_chapter": summary.to_dict(orient="records"),
        "breakdown": df.to_dict(orient="records")
    }


# ── Projects ─────────────────────────────────────────────────

@app.get("/projects", tags=["Projects"])
def get_all_projects(
    chapter:       Optional[str] = Query(None),
    thematic_area: Optional[str] = Query(None, description="e.g. Health, Education, WASH"),
    status:        Optional[str] = Query(None, description="active, completed, planned")
):
    sql = "SELECT * FROM projects WHERE 1=1"
    if thematic_area:
        sql += f" AND thematic_area ILIKE '%{thematic_area}%'"
    if status:
        sql += f" AND status = '{status}'"

    df = query_node(chapter, sql) if chapter else query_all_nodes(sql)
    return {
        "total": len(df),
        "data": df.to_dict(orient="records")
    }

@app.get("/projects/summary", tags=["Projects"])
def projects_summary():
    sql = """
        SELECT thematic_area, status, COUNT(*) as count,
               SUM(budget_ksh) as total_budget_ksh
        FROM projects
        GROUP BY thematic_area, status
    """
    df = query_all_nodes(sql)
    df = df.groupby(["thematic_area","status"]).agg(
        count=("count","sum"),
        total_budget_ksh=("total_budget_ksh","sum")
    ).reset_index()
    return {
        "total_projects": int(df["count"].sum()),
        "total_budget_ksh": float(df["total_budget_ksh"].sum()),
        "breakdown": df.to_dict(orient="records")
    }


# ── Funds ────────────────────────────────────────────────────

@app.get("/funds", tags=["Funds"])
def get_all_funds(
    chapter:   Optional[str] = Query(None),
    fund_type: Optional[str] = Query(None, description="grant, donation, government, internal"),
    donor:     Optional[str] = Query(None)
):
    sql = "SELECT * FROM funds WHERE 1=1"
    if fund_type:
        sql += f" AND fund_type = '{fund_type}'"
    if donor:
        sql += f" AND donor_name ILIKE '%{donor}%'"

    df = query_node(chapter, sql) if chapter else query_all_nodes(sql)
    return {
        "total_records": len(df),
        "total_amount_ksh": float(df["amount_ksh"].sum()) if not df.empty else 0,
        "data": df.to_dict(orient="records")
    }

@app.get("/funds/by-donor", tags=["Funds"])
def funds_by_donor():
    sql = "SELECT donor_name, fund_type, SUM(amount_ksh) as total_ksh, COUNT(*) as transactions FROM funds GROUP BY donor_name, fund_type"
    df  = query_all_nodes(sql)
    df  = df.groupby(["donor_name","fund_type"]).agg(
        total_ksh=("total_ksh","sum"),
        transactions=("transactions","sum")
    ).reset_index().sort_values("total_ksh", ascending=False)
    return {
        "total_donors": len(df),
        "data": df.to_dict(orient="records")
    }


# ── Services ─────────────────────────────────────────────────

@app.get("/services", tags=["Services"])
def get_services(
    chapter:      Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    limit:        int           = Query(100, le=500)
):
    sql = f"SELECT * FROM services LIMIT {limit}"
    if service_type:
        sql = f"SELECT * FROM services WHERE service_type ILIKE '%{service_type}%' LIMIT {limit}"

    df = query_node(chapter, sql) if chapter else query_all_nodes(sql)
    return {
        "total": len(df),
        "data": df.to_dict(orient="records")
    }

@app.get("/services/summary", tags=["Services"])
def services_summary():
    sql = "SELECT service_type, COUNT(*) as count FROM services GROUP BY service_type ORDER BY count DESC"
    df  = query_all_nodes(sql)
    df  = df.groupby("service_type")["count"].sum().reset_index().sort_values("count", ascending=False)
    return {
        "total_services": int(df["count"].sum()),
        "by_type": df.to_dict(orient="records")
    }


# ── KPI Dashboard endpoint ───────────────────────────────────

@app.get("/kpi", tags=["Dashboard"])
def get_kpi_summary():
    ben  = query_all_nodes("SELECT COUNT(*) as c FROM beneficiaries WHERE is_active=TRUE")
    proj = query_all_nodes("SELECT COUNT(*) as c FROM projects")
    svc  = query_all_nodes("SELECT COUNT(*) as c FROM services")
    funds= query_all_nodes("SELECT SUM(amount_ksh) as c FROM funds")

    return {
        "total_beneficiaries":   int(ben["c"].sum()),
        "total_projects":        int(proj["c"].sum()),
        "total_services":        int(svc["c"].sum()),
        "total_funding_ksh":     float(funds["c"].sum()),
        "total_funding_usd":     round(float(funds["c"].sum()) / 130, 2),
        "chapters_online":       len(CHAPTER_NODES),
    }