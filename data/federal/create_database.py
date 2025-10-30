#!/usr/bin/env python3
"""
Script to create the prep_federal_layer.sqlite database and populate it with data.
"""

import csv
import sqlite3
from pathlib import Path

# Database file path
DB_PATH = Path(__file__).parent / "prep_federal_layer.sqlite"

# Remove existing database
if DB_PATH.exists():
    DB_PATH.unlink()

# Create database and tables
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create accreditation_bodies table
cursor.execute("""
CREATE TABLE accreditation_bodies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    url TEXT,
    email TEXT,
    contact TEXT
)
""")

# Create certification_bodies table
cursor.execute("""
CREATE TABLE certification_bodies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    url TEXT,
    email TEXT
)
""")

# Create scopes table
cursor.execute("""
CREATE TABLE scopes (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    cfr_title_part_section TEXT,
    program_reference TEXT,
    notes TEXT
)
""")

# Create ab_cb_scope_links table
cursor.execute("""
CREATE TABLE ab_cb_scope_links (
    id INTEGER PRIMARY KEY,
    accreditation_body_id INTEGER NOT NULL,
    certification_body_id INTEGER NOT NULL,
    scope_id INTEGER NOT NULL,
    recognition_initial_date DATE,
    recognition_expiration_date DATE,
    scope_status TEXT,
    source TEXT,
    FOREIGN KEY (accreditation_body_id) REFERENCES accreditation_bodies(id),
    FOREIGN KEY (certification_body_id) REFERENCES certification_bodies(id),
    FOREIGN KEY (scope_id) REFERENCES scopes(id)
)
""")

# Create indexes
cursor.execute("""
CREATE INDEX idx_links_expiry ON ab_cb_scope_links(recognition_expiration_date)
""")

cursor.execute("""
CREATE INDEX idx_links_scope ON ab_cb_scope_links(scope_id)
""")

cursor.execute("""
CREATE INDEX idx_links_ab ON ab_cb_scope_links(accreditation_body_id)
""")

cursor.execute("""
CREATE INDEX idx_links_cb ON ab_cb_scope_links(certification_body_id)
""")

# Populate accreditation_bodies
with open(Path(__file__).parent / "ab_table.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute(
            "INSERT INTO accreditation_bodies (id, name, url, email, contact) VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["name"], row["url"], row["email"], row["contact"])
        )

# Populate certification_bodies
with open(Path(__file__).parent / "certification_bodies.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute(
            "INSERT INTO certification_bodies (id, name, url, email) VALUES (?, ?, ?, ?)",
            (row["id"], row["name"], row["url"], row["email"])
        )

# Populate scopes
with open(Path(__file__).parent / "scopes.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute(
            "INSERT INTO scopes (id, name, cfr_title_part_section, program_reference, notes) VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["name"], row["cfr_title_part_section"], row["program_reference"], row["notes"])
        )

# Populate ab_cb_scope_links
with open(Path(__file__).parent / "accreditor_certifier_scope_links.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute(
            """INSERT INTO ab_cb_scope_links
            (id, accreditation_body_id, certification_body_id, scope_id,
             recognition_initial_date, recognition_expiration_date, scope_status, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["id"], row["accreditation_body_id"], row["certification_body_id"],
             row["scope_id"], row["recognition_initial_date"], row["recognition_expiration_date"],
             row["scope_status"], row["source"])
        )

conn.commit()

# Verify data
print(f"Database created: {DB_PATH}")
print(f"Accreditation Bodies: {cursor.execute('SELECT COUNT(*) FROM accreditation_bodies').fetchone()[0]}")
print(f"Certification Bodies: {cursor.execute('SELECT COUNT(*) FROM certification_bodies').fetchone()[0]}")
print(f"Scopes: {cursor.execute('SELECT COUNT(*) FROM scopes').fetchone()[0]}")
print(f"Links: {cursor.execute('SELECT COUNT(*) FROM ab_cb_scope_links').fetchone()[0]}")

conn.close()
