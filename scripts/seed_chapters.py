import duckdb
import random
from datetime import date, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
NODES_DIR = BASE_DIR / "chapter_nodes"
SCHEMA_FILE = NODES_DIR / "schema.sql"
NODES_DIR.mkdir(exist_ok=True)

# ── Chapter config ───────────────────────────────────────────
CHAPTERS = {
    "nairobi": {
        "db":      NODES_DIR / "nairobi.duckdb",
        "name":    "Nairobi HQ",
        "region":  "Nairobi",
        "county":  "Nairobi",
        "is_hq":   True,
        "counties": ["Nairobi", "Kiambu", "Machakos"],
    },
    "kisumu": {
        "db":      NODES_DIR / "kisumu.duckdb",
        "name":    "Kisumu Chapter",
        "region":  "Nyanza",
        "county":  "Kisumu",
        "is_hq":   False,
        "counties": ["Kisumu", "Siaya", "Homa Bay", "Migori"],
    },
    "mombasa": {
        "db":      NODES_DIR / "mombasa.duckdb",
        "name":    "Mombasa Chapter",
        "region":  "Coast",
        "county":  "Mombasa",
        "is_hq":   False,
        "counties": ["Mombasa", "Kilifi", "Kwale", "Taita Taveta"],
    },
}

# ── Realistic data pools ─────────────────────────────────────
KENYAN_NAMES = [
    "Akinyi Otieno","Wanjiru Kamau","Mwangi Njoroge","Adhiambo Odhiambo",
    "Kipchoge Ruto","Njeri Kariuki","Omondi Oluoch","Wairimu Gitau",
    "Mutua Musyoka","Auma Obama","Chebet Korir","Waweru Ndungu",
    "Atieno Awino","Kamande Gacheru","Moraa Nyamweya","Odongo Ouma",
    "Wangari Mwai","Juma Bakari","Zawadi Hassan","Baraka Mwangi",
    "Fatuma Ali","Hamisi Salim","Kerubo Nyaboke","Luhya Simiyu",
    "Mwenda Kirimi","Njagi Muriuki","Onyango Okello","Purity Wanjiku",
    "Riziki Charo","Shiro Waithaka",
]

PROJECTS = [
    ("Clean Water Access Programme",        "WASH",        2_500_000),
    ("Girls Education Bursary Fund",         "Education",   1_800_000),
    ("Community Health Outreach",            "Health",      3_200_000),
    ("Smallholder Farmer Support",           "Agriculture", 2_100_000),
    ("Youth Vocational Training",            "Livelihoods", 1_500_000),
    ("GBV Survivor Support Network",         "Protection",  1_200_000),
    ("Early Childhood Development Centres",  "Education",     980_000),
    ("Nutrition & Food Security Drive",      "Health",      1_750_000),
]

DONORS = [
    ("USAID Kenya",                              "grant"),
    ("UKAID / FCDO",                             "grant"),
    ("Kenya Community Development Foundation",   "donation"),
    ("African Development Bank",                 "grant"),
    ("Safaricom Foundation",                     "donation"),
    ("Government of Kenya - Social Protection",  "government"),
    ("Gates Foundation",                         "grant"),
    ("UNICEF Kenya",                             "grant"),
]

SERVICE_TYPES = [
    "Medical consultation","Bursary disbursement","Vocational training session",
    "Water point installation","Agricultural input distribution",
    "Legal aid referral","Counselling session","Food basket distribution",
    "Child protection case management","Livelihood cash transfer",
]

ROLES = [
    "Programme Officer","M&E Officer","Finance Officer",
    "Community Health Worker","Field Coordinator","Data Clerk",
    "Protection Officer","WASH Engineer","Nutrition Officer","Driver",
]

STATUSES = ["active", "active", "completed", "planned"]

def random_date(start_year=2021, end_year=2024):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def seed_chapter(key):
    cfg  = CHAPTERS[key]
    schema = SCHEMA_FILE.read_text()
    con  = duckdb.connect(str(cfg["db"]))
    con.execute(schema)
    print(f"\n  Seeding {cfg['name']} ...")

    # Chapter record
    con.execute("""
        INSERT OR IGNORE INTO chapters
            (chapter_id, chapter_name, region, county, established_on, contact_email, is_hq)
        VALUES (1, ?, ?, ?, ?, ?, ?)
    """, [cfg["name"], cfg["region"], cfg["county"],
          date(2015, 3, 1), f"info@ngo-{key}.or.ke", cfg["is_hq"]])

    # Staff — 15 per chapter
    for i in range(1, 16):
        name = random.choice(KENYAN_NAMES)
        con.execute("""
            INSERT INTO staff
                (staff_id, full_name, role, email, phone, joined_on, is_active)
            VALUES (?, ?, ?, ?, ?, ?, TRUE)
        """, [i, name, random.choice(ROLES),
              name.lower().replace(" ", ".") + f"{i}@ngo.or.ke",
              f"+2547{random.randint(10000000,99999999)}",
              random_date(2015, 2022)])

    # Beneficiaries — 200 per chapter
    for i in range(1, 201):
        name   = random.choice(KENYAN_NAMES)
        county = random.choice(cfg["counties"])
        dob    = date(random.randint(1970,2005),
                      random.randint(1,12),
                      random.randint(1,28))
        con.execute("""
            INSERT INTO beneficiaries
                (beneficiary_id, full_name, gender, date_of_birth,
                 county, sub_county, phone, registered_on, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRUE)
        """, [i, name, random.choice(["Male","Female"]), dob,
              county, f"{county} Central",
              f"+2547{random.randint(10000000,99999999)}",
              random_date(2021, 2024)])

    # Projects — 4 per chapter
    chosen = random.sample(PROJECTS, 4)
    for i, (pname, theme, budget) in enumerate(chosen, start=1):
        start = random_date(2021, 2023)
        con.execute("""
            INSERT INTO projects
                (project_id, project_name, description, start_date, end_date,
                 budget_ksh, status, thematic_area)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [i, pname,
              f"{pname} serving {cfg['county']} and surrounding counties.",
              start, start + timedelta(days=365),
              budget + random.randint(-200_000, 200_000),
              random.choice(STATUSES), theme])

    # Funds — 2 to 3 per project
    fund_id = 1
    for pid in range(1, 5):
        for _ in range(random.randint(2, 3)):
            donor, ftype = random.choice(DONORS)
            con.execute("""
                INSERT INTO funds
                    (fund_id, project_id, donor_name, amount_ksh,
                     currency, received_on, fund_type)
                VALUES (?, ?, ?, ?, 'KES', ?, ?)
            """, [fund_id, pid, donor,
                  round(random.uniform(200_000, 900_000), 2),
                  random_date(2021, 2024), ftype])
            fund_id += 1

    # Services — 500 per chapter
    for i in range(1, 501):
        con.execute("""
            INSERT INTO services
                (service_id, beneficiary_id, project_id, service_type,
                 service_date, location, delivered_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [i,
              random.randint(1, 200),
              random.randint(1, 4),
              random.choice(SERVICE_TYPES),
              random_date(2021, 2024),
              random.choice(cfg["counties"]),
              random.choice(KENYAN_NAMES),
              "Routine service delivery"])

    con.close()
    print(f"     Done — 200 beneficiaries, 4 projects, 500 services, 15 staff seeded.")

if __name__ == "__main__":
    for key in CHAPTERS:
        seed_chapter(key)
    print("\n All 3 chapter databases seeded successfully!")
    print(f"   Files saved in: {NODES_DIR}")