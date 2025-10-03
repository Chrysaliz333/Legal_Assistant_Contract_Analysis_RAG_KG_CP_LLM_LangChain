"""
SQLite version of the schema - works without Docker/PostgreSQL
Usage: python3 setup_sqlite.py
"""

import sqlite3
import csv
import json

DB_PATH = "../legal_assistant.db"

def setup_database():
    """Create tables and load sample data into SQLite"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create policies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            policy_text TEXT NOT NULL,
            policy_category TEXT,
            severity_default TEXT CHECK (severity_default IN ('low','medium','high','critical')) NOT NULL
        )
    """)

    # Create playbook_rules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playbook_rules (
            rule_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            rule_text TEXT NOT NULL,
            applicable_contract_types TEXT,  -- JSON array as text
            applicable_clauses TEXT,  -- JSON array as text
            severity_override TEXT CHECK (severity_override IN ('low','medium','high','critical')),
            conditions TEXT,  -- JSON object as text
            model_orientation TEXT CHECK (model_orientation IN ('buy','sell')) NOT NULL
        )
    """)

    # Load policies from CSV
    with open('policies_light.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO policies (policy_text, policy_category, severity_default)
                VALUES (?, ?, ?)
            """, (
                row['policy_text'],
                row.get('policy_category'),
                row.get('severity_default', 'medium')
            ))

    # Load playbook rules from CSV
    with open('playbook_rules_light.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert semicolon-separated lists to JSON arrays
            contract_types = json.dumps([x.strip() for x in row.get('applicable_contract_types', '').split(';') if x.strip()])
            clauses = json.dumps([x.strip() for x in row.get('applicable_clauses', '').split(';') if x.strip()])

            cursor.execute("""
                INSERT INTO playbook_rules (
                    rule_text, applicable_contract_types, applicable_clauses,
                    severity_override, conditions, model_orientation
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row['rule_text'],
                contract_types,
                clauses,
                row.get('severity_override') or None,
                row.get('conditions', '{}'),
                row['model_orientation']
            ))

    conn.commit()

    # Verify data loaded
    cursor.execute("SELECT COUNT(*) FROM policies")
    policy_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM playbook_rules")
    rule_count = cursor.fetchone()[0]

    print(f"✅ Database created at: {DB_PATH}")
    print(f"✅ Loaded {policy_count} policies")
    print(f"✅ Loaded {rule_count} playbook rules")

    # Show sample data
    print("\n📋 Sample Policies:")
    cursor.execute("SELECT policy_text, severity_default FROM policies LIMIT 2")
    for text, severity in cursor.fetchall():
        print(f"  - [{severity.upper()}] {text[:80]}...")

    print("\n📋 Sample Playbook Rules:")
    cursor.execute("SELECT rule_text, model_orientation FROM playbook_rules LIMIT 2")
    for text, orientation in cursor.fetchall():
        print(f"  - [{orientation.upper()}] {text[:80]}...")

    conn.close()

if __name__ == "__main__":
    setup_database()
