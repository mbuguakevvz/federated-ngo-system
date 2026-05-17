# ================================================================
# NGO Federated Data System — Dashboard
# Reads from central warehouse and serves live KPI charts
# ================================================================

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import duckdb
import plotly.graph_objects as go
import plotly.express as px
import json

app = FastAPI(title="NGO Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WAREHOUSE_DB = Path(__file__).parent.parent / "warehouse" / "ngo_warehouse.duckdb"

def wh():
    return duckdb.connect(str(WAREHOUSE_DB), read_only=True)

def to_json(fig):
    return fig.to_json()

import plotly

# ── Data queries ─────────────────────────────────────────────
def get_kpis():
    con = wh()
    kpis = {
        "beneficiaries": con.execute("SELECT COUNT(*) FROM dim_beneficiary").fetchone()[0],
        "projects":      con.execute("SELECT COUNT(*) FROM dim_project").fetchone()[0],
        "services":      con.execute("SELECT COUNT(*) FROM fact_services").fetchone()[0],
        "funding_ksh":   con.execute("SELECT COALESCE(SUM(amount_ksh),0) FROM fact_funds").fetchone()[0],
    }
    con.close()
    return kpis

def chart_services_by_type():
    con = wh()
    df  = con.execute("""
        SELECT service_type, COUNT(*) as count
        FROM fact_services
        GROUP BY service_type ORDER BY count DESC
    """).df()
    con.close()
    fig = px.bar(df, x="service_type", y="count",
                 title="Services Delivered by Type",
                 color="count", color_continuous_scale="teal",
                 labels={"service_type": "Service", "count": "Count"})
    fig.update_layout(showlegend=False, plot_bgcolor="white",
                      xaxis_tickangle=-35, margin=dict(t=50,b=120))
    return to_json(fig)

def chart_funding_by_donor():
    con = wh()
    df  = con.execute("""
        SELECT donor_name, SUM(amount_ksh) as total
        FROM fact_funds
        GROUP BY donor_name ORDER BY total DESC LIMIT 8
    """).df()
    con.close()
    fig = px.pie(df, names="donor_name", values="total",
                 title="Funding by Donor (KES)",
                 color_discrete_sequence=px.colors.sequential.Teal)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(t=50,b=20))
    return to_json(fig)

def chart_beneficiaries_by_chapter():
    con = wh()
    df  = con.execute("""
        SELECT b.source_node as chapter, b.gender, COUNT(*) as count
        FROM dim_beneficiary b
        GROUP BY b.source_node, b.gender
    """).df()
    con.close()
    fig = px.bar(df, x="chapter", y="count", color="gender",
                 title="Beneficiaries by Chapter & Gender",
                 barmode="group",
                 color_discrete_map={"Male":"#0e7c7b","Female":"#f4a261"},
                 labels={"chapter":"Chapter","count":"Beneficiaries"})
    fig.update_layout(plot_bgcolor="white", margin=dict(t=50,b=40))
    return to_json(fig)

def chart_services_over_time():
    con = wh()
    df  = con.execute("""
        SELECT d.year, d.month, d.month_name, COUNT(*) as count
        FROM fact_services f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
    """).df()
    con.close()
    df["period"] = df["month_name"].str[:3] + " " + df["year"].astype(str)
    fig = px.line(df, x="period", y="count",
                  title="Services Delivered Over Time",
                  markers=True,
                  labels={"period":"Month","count":"Services"})
    fig.update_traces(line_color="#0e7c7b", line_width=2.5)
    fig.update_layout(plot_bgcolor="white", margin=dict(t=50,b=60),
                      xaxis_tickangle=-45)
    return to_json(fig)

def chart_projects_by_theme():
    con = wh()
    df  = con.execute("""
        SELECT thematic_area, status, COUNT(*) as count
        FROM dim_project
        GROUP BY thematic_area, status
    """).df()
    con.close()
    fig = px.bar(df, x="thematic_area", y="count", color="status",
                 title="Projects by Thematic Area & Status",
                 barmode="stack",
                 labels={"thematic_area":"Theme","count":"Projects"})
    fig.update_layout(plot_bgcolor="white", margin=dict(t=50,b=60))
    return to_json(fig)

def chart_age_groups():
    con = wh()
    df  = con.execute("""
        SELECT age_group, COUNT(*) as count
        FROM dim_beneficiary
        GROUP BY age_group ORDER BY count DESC
    """).df()
    con.close()
    fig = px.pie(df, names="age_group", values="count",
                 title="Beneficiaries by Age Group",
                 hole=0.4,
                 color_discrete_sequence=px.colors.sequential.Teal)
    fig.update_layout(margin=dict(t=50,b=20))
    return to_json(fig)


# ── Dashboard HTML ───────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    kpis   = get_kpis()
    c1     = chart_services_by_type()
    c2     = chart_funding_by_donor()
    c3     = chart_beneficiaries_by_chapter()
    c4     = chart_services_over_time()
    c5     = chart_projects_by_theme()
    c6     = chart_age_groups()

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>NGO Federated Data Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #1a202c; }}
    header {{
      background: linear-gradient(135deg, #0e7c7b, #145a5a);
      color: white; padding: 24px 32px;
      display: flex; align-items: center; gap: 16px;
    }}
    header h1 {{ font-size: 1.6rem; font-weight: 700; }}
    header p  {{ font-size: 0.85rem; opacity: 0.85; margin-top: 4px; }}
    .badge {{
      background: rgba(255,255,255,0.2); border-radius: 20px;
      padding: 4px 14px; font-size: 0.78rem; margin-left: auto;
    }}
    .kpi-row {{
      display: grid; grid-template-columns: repeat(4,1fr);
      gap: 16px; padding: 24px 32px 8px;
    }}
    .kpi {{
      background: white; border-radius: 12px;
      padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      border-left: 5px solid #0e7c7b;
    }}
    .kpi .label {{ font-size: 0.78rem; color: #718096; text-transform: uppercase; letter-spacing: .05em; }}
    .kpi .value {{ font-size: 2rem; font-weight: 700; color: #0e7c7b; margin-top: 6px; }}
    .kpi .sub   {{ font-size: 0.78rem; color: #a0aec0; margin-top: 4px; }}
    .charts {{
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 16px; padding: 16px 32px 32px;
    }}
    .chart-card {{
      background: white; border-radius: 12px;
      padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}
    .chart-card.wide {{ grid-column: span 2; }}
    footer {{
      text-align: center; padding: 16px;
      font-size: 0.78rem; color: #a0aec0;
    }}
  </style>
</head>
<body>

<header>
  <div>
    <h1>🌍 NGO Federated Data Dashboard</h1>
    <p>Cross-chapter analytics — Nairobi · Kisumu · Mombasa</p>
  </div>
  <div class="badge">3 Chapters Online</div>
</header>

<div class="kpi-row">
  <div class="kpi">
    <div class="label">Total Beneficiaries</div>
    <div class="value">{kpis['beneficiaries']:,}</div>
    <div class="sub">Across all chapters</div>
  </div>
  <div class="kpi">
    <div class="label">Active Projects</div>
    <div class="value">{kpis['projects']:,}</div>
    <div class="sub">All thematic areas</div>
  </div>
  <div class="kpi">
    <div class="label">Services Delivered</div>
    <div class="value">{kpis['services']:,}</div>
    <div class="sub">Total service records</div>
  </div>
  <div class="kpi">
    <div class="label">Total Funding</div>
    <div class="value">KES {kpis['funding_ksh']/1_000_000:.1f}M</div>
    <div class="sub">≈ USD {kpis['funding_ksh']/130:,.0f}</div>
  </div>
</div>

<div class="charts">
  <div class="chart-card wide"><div id="c4"></div></div>
  <div class="chart-card"><div id="c1"></div></div>
  <div class="chart-card"><div id="c2"></div></div>
  <div class="chart-card"><div id="c3"></div></div>
  <div class="chart-card"><div id="c6"></div></div>
  <div class="chart-card wide"><div id="c5"></div></div>
</div>

<footer>Federated NGO Data System · Built by Kevin Mbugua · github.com/mbuguakevvz</footer>

<script>
  Plotly.newPlot('c1', {c1});
  Plotly.newPlot('c2', {c2});
  Plotly.newPlot('c3', {c3});
  Plotly.newPlot('c4', {c4});
  Plotly.newPlot('c5', {c5});
  Plotly.newPlot('c6', {c6});
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)