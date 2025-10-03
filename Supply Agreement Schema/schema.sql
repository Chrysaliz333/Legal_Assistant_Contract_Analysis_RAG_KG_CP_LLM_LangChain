-- Light v0 schema
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for gen_random_uuid()

-- Broad organizational policies
CREATE TABLE IF NOT EXISTS policies (
  policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_text TEXT NOT NULL,
  policy_category TEXT,
  severity_default TEXT CHECK (severity_default IN ('low','medium','high','critical')) NOT NULL
);

-- Specific playbook rules
CREATE TABLE IF NOT EXISTS playbook_rules (
  rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_text TEXT NOT NULL,
  applicable_contract_types TEXT[] DEFAULT '{}',
  applicable_clauses TEXT[] DEFAULT '{}',
  severity_override TEXT CHECK (severity_override IN ('low','medium','high','critical')),
  conditions JSONB DEFAULT '{}'::jsonb,
  model_orientation TEXT CHECK (model_orientation IN ('buy','sell')) NOT NULL
);

-- Unified read model for the agent
CREATE OR REPLACE VIEW combined_rules AS
SELECT policy_id::text AS id,'policy' AS kind,policy_text AS text,
       policy_category AS category, severity_default AS severity,
       '{}'::jsonb AS conditions, NULL::text AS model_orientation,
       ARRAY[]::text[] AS applicable_contract_types, ARRAY[]::text[] AS applicable_clauses
FROM policies
UNION ALL
SELECT rule_id::text,'playbook',rule_text,
       (CASE WHEN array_length(applicable_clauses,1) >= 1
             THEN applicable_clauses[1] ELSE NULL END) AS category,
       COALESCE(severity_override,'medium') AS severity,
       conditions, model_orientation,
       applicable_contract_types, applicable_clauses
FROM playbook_rules;