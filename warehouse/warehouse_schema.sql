-- ============================================================
-- Central Data Warehouse — Star Schema
-- Federated NGO Data System
-- ============================================================

-- Dimension: Chapters
CREATE TABLE IF NOT EXISTS dim_chapter (
    chapter_key     INTEGER PRIMARY KEY,
    chapter_id      INTEGER,
    chapter_name    VARCHAR,
    region          VARCHAR,
    county          VARCHAR,
    is_hq           BOOLEAN,
    source_node     VARCHAR
);

-- Dimension: Beneficiaries
CREATE TABLE IF NOT EXISTS dim_beneficiary (
    beneficiary_key INTEGER PRIMARY KEY,
    beneficiary_id  INTEGER,
    full_name       VARCHAR,
    gender          VARCHAR,
    date_of_birth   DATE,
    age_group       VARCHAR,
    county          VARCHAR,
    sub_county      VARCHAR,
    source_node     VARCHAR
);

-- Dimension: Projects
CREATE TABLE IF NOT EXISTS dim_project (
    project_key     INTEGER PRIMARY KEY,
    project_id      INTEGER,
    project_name    VARCHAR,
    thematic_area   VARCHAR,
    status          VARCHAR,
    start_date      DATE,
    end_date        DATE,
    budget_ksh      DECIMAL(15,2),
    source_node     VARCHAR
);

-- Dimension: Date
CREATE TABLE IF NOT EXISTS dim_date (
    date_key        INTEGER PRIMARY KEY,
    full_date       DATE,
    year            INTEGER,
    quarter         INTEGER,
    month           INTEGER,
    month_name      VARCHAR,
    week            INTEGER,
    day_of_week     VARCHAR
);

-- Fact: Services delivered
CREATE TABLE IF NOT EXISTS fact_services (
    service_key     INTEGER PRIMARY KEY,
    service_id      INTEGER,
    beneficiary_key INTEGER REFERENCES dim_beneficiary(beneficiary_key),
    project_key     INTEGER REFERENCES dim_project(project_key),
    chapter_key     INTEGER REFERENCES dim_chapter(chapter_key),
    date_key        INTEGER REFERENCES dim_date(date_key),
    service_type    VARCHAR,
    location        VARCHAR,
    source_node     VARCHAR
);

-- Fact: Funds received
CREATE TABLE IF NOT EXISTS fact_funds (
    fund_key        INTEGER PRIMARY KEY,
    fund_id         INTEGER,
    project_key     INTEGER REFERENCES dim_project(project_key),
    chapter_key     INTEGER REFERENCES dim_chapter(chapter_key),
    date_key        INTEGER REFERENCES dim_date(date_key),
    donor_name      VARCHAR,
    fund_type       VARCHAR,
    amount_ksh      DECIMAL(15,2),
    source_node     VARCHAR
);

-- Audit log
CREATE TABLE IF NOT EXISTS etl_audit_log (
    log_id          INTEGER PRIMARY KEY,
    run_timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chapter         VARCHAR,
    table_name      VARCHAR,
    rows_loaded     INTEGER,
    status          VARCHAR,
    notes           VARCHAR
);