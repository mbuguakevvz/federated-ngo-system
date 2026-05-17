CREATE TABLE IF NOT EXISTS chapters (
    chapter_id      INTEGER PRIMARY KEY,
    chapter_name    VARCHAR,
    region          VARCHAR,
    county          VARCHAR,
    established_on  DATE,
    contact_email   VARCHAR,
    is_hq           BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS beneficiaries (
    beneficiary_id  INTEGER PRIMARY KEY,
    full_name       VARCHAR NOT NULL,
    gender          VARCHAR,
    date_of_birth   DATE,
    county          VARCHAR,
    sub_county      VARCHAR,
    phone           VARCHAR,
    registered_on   DATE,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS projects (
    project_id      INTEGER PRIMARY KEY,
    project_name    VARCHAR NOT NULL,
    description     VARCHAR,
    start_date      DATE,
    end_date        DATE,
    budget_ksh      DECIMAL(15,2),
    status          VARCHAR,
    thematic_area   VARCHAR
);

CREATE TABLE IF NOT EXISTS services (
    service_id      INTEGER PRIMARY KEY,
    beneficiary_id  INTEGER REFERENCES beneficiaries(beneficiary_id),
    project_id      INTEGER REFERENCES projects(project_id),
    service_type    VARCHAR,
    service_date    DATE,
    location        VARCHAR,
    delivered_by    VARCHAR,
    notes           VARCHAR
);

CREATE TABLE IF NOT EXISTS funds (
    fund_id         INTEGER PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(project_id),
    donor_name      VARCHAR,
    amount_ksh      DECIMAL(15,2),
    currency        VARCHAR DEFAULT 'KES',
    received_on     DATE,
    fund_type       VARCHAR
);

CREATE TABLE IF NOT EXISTS staff (
    staff_id        INTEGER PRIMARY KEY,
    full_name       VARCHAR,
    role            VARCHAR,
    email           VARCHAR,
    phone           VARCHAR,
    joined_on       DATE,
    is_active       BOOLEAN DEFAULT TRUE
);