import os
import csv
import json
import psycopg2
import psycopg2.extras as extras

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", "contracts")
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASS = os.getenv("PGPASSWORD", "postgres")

POLICIES_CSV = os.getenv("POLICIES_CSV", "policies_light.csv")
PLAYBOOK_CSV = os.getenv("PLAYBOOK_CSV", "playbook_rules_light.csv")

def connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def run_sql(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()

def load_policies(conn, csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [(
            r["policy_text"],
            r.get("policy_category"),
            r.get("severity_default","medium"),
        ) for r in reader]
    with conn.cursor() as cur:
        extras.execute_values(cur, '''
            INSERT INTO policies (policy_text, policy_category, severity_default)
            VALUES %s
        ''', rows)
    conn.commit()

def _split_list(val):
    if not val:
        return []
    return [x.strip() for x in str(val).split(";") if x.strip()]

def load_playbook(conn, csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append((
                r["rule_text"],
                _split_list(r.get("applicable_contract_types","")),
                _split_list(r.get("applicable_clauses","")),
                r.get("severity_override") or None,
                json.loads(r.get("conditions") or "{}"),
                r["model_orientation"],
            ))
    with conn.cursor() as cur:
        extras.execute_values(cur, '''
            INSERT INTO playbook_rules (
              rule_text, applicable_contract_types, applicable_clauses,
              severity_override, conditions, model_orientation
            )
            VALUES %s
        ''', rows)
    conn.commit()

def main():
    schema_sql = open("schema.sql","r",encoding="utf-8").read()
    with connect() as conn:
        run_sql(conn, schema_sql)
        load_policies(conn, POLICIES_CSV)
        load_playbook(conn, PLAYBOOK_CSV)
    print("Import complete.")

if __name__ == "__main__":
    main()