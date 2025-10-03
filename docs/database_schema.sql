-- ============================================================================
-- Legal Assistant Multi-Session Continuity Database Schema
-- PostgreSQL 14+ with JSON support
-- Version: 1.0
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS AND AUTHENTICATION
-- ============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('viewer', 'reviewer', 'editor', 'approver', 'admin')),
    organization_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);

-- ============================================================================
-- ORGANIZATIONS AND SETTINGS
-- ============================================================================

CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    default_style_params JSONB DEFAULT '{
        "tone": "concise",
        "formality": "legal",
        "aggressiveness": "balanced",
        "audience": "internal"
    }'::jsonb,
    CONSTRAINT valid_style_params CHECK (
        jsonb_typeof(default_style_params) = 'object'
    )
);

-- ============================================================================
-- NEGOTIATION SESSIONS
-- ============================================================================

CREATE TABLE negotiation_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(organization_id),
    contract_name VARCHAR(500) NOT NULL,
    counterparty_id UUID, -- Foreign key to counterparties table
    matter_id VARCHAR(100), -- External matter reference
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'cancelled')),
    current_version_id UUID, -- Set after first version created
    style_overrides JSONB DEFAULT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_org ON negotiation_sessions(organization_id);
CREATE INDEX idx_sessions_counterparty ON negotiation_sessions(counterparty_id);
CREATE INDEX idx_sessions_status ON negotiation_sessions(status);

-- ============================================================================
-- DOCUMENT VERSIONS (REQ-VC-001)
-- ============================================================================

CREATE TABLE document_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES negotiation_sessions(session_id) ON DELETE CASCADE,
    parent_version_id UUID REFERENCES document_versions(version_id),
    version_number INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source VARCHAR(50) NOT NULL CHECK (source IN ('internal', 'counterparty')),
    document_hash VARCHAR(64) NOT NULL, -- SHA-256 hash
    file_path TEXT NOT NULL, -- S3 path or local path
    file_name VARCHAR(500),
    uploader_id UUID REFERENCES users(user_id),
    rollback_to UUID REFERENCES document_versions(version_id), -- Non-null if this is a rollback
    rollback_reason TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT unique_version_number_per_session UNIQUE (session_id, version_number)
);

CREATE INDEX idx_versions_session ON document_versions(session_id);
CREATE INDEX idx_versions_parent ON document_versions(parent_version_id);
CREATE INDEX idx_versions_hash ON document_versions(document_hash);
CREATE INDEX idx_versions_timestamp ON document_versions(timestamp DESC);

-- ============================================================================
-- CLAUSES AND ANNOTATIONS (REQ-VC-002)
-- ============================================================================

CREATE TABLE clauses (
    clause_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES document_versions(version_id) ON DELETE CASCADE,
    clause_identifier VARCHAR(100) NOT NULL, -- e.g., "5.1", "Limitation of Liability"
    clause_type VARCHAR(100), -- e.g., "liability", "termination", "confidentiality"
    clause_text TEXT NOT NULL,
    char_start INTEGER,
    char_end INTEGER,
    xpath TEXT,
    paragraph_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_clauses_version ON clauses(version_id);
CREATE INDEX idx_clauses_type ON clauses(clause_type);
CREATE INDEX idx_clauses_identifier ON clauses(clause_identifier);

CREATE TABLE annotations (
    annotation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES document_versions(version_id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses(clause_id) ON DELETE SET NULL,
    anchor_method VARCHAR(50) CHECK (anchor_method IN ('xpath', 'paragraph_id', 'char_offset')),
    anchor_value TEXT NOT NULL,
    annotation_type VARCHAR(50) NOT NULL CHECK (annotation_type IN ('comment', 'redline')),
    content JSONB NOT NULL,
    author_id UUID REFERENCES users(user_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_annotation_content CHECK (
        jsonb_typeof(content) = 'object' AND
        content ? 'text'
    )
);

CREATE INDEX idx_annotations_version ON annotations(version_id);
CREATE INDEX idx_annotations_clause ON annotations(clause_id);
CREATE INDEX idx_annotations_author ON annotations(author_id);

-- ============================================================================
-- NEGOTIATION HISTORY LOG (REQ-VC-004)
-- ============================================================================

CREATE TABLE negotiation_log (
    log_entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES negotiation_sessions(session_id) ON DELETE CASCADE,
    version_id UUID REFERENCES document_versions(version_id) ON DELETE SET NULL,
    clause_id UUID REFERENCES clauses(clause_id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL CHECK (change_type IN ('insertion', 'deletion', 'modification', 'status_change', 'version_creation', 'rollback')),
    before_state JSONB,
    after_state JSONB,
    rationale_id UUID, -- References neutral_rationale table
    source VARCHAR(50) NOT NULL CHECK (source IN ('internal', 'counterparty')),
    status VARCHAR(50) CHECK (status IN ('pending', 'accepted', 'rejected', 'superseded')),
    actor_id UUID REFERENCES users(user_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    signature VARCHAR(128) -- Optional cryptographic signature
);

CREATE INDEX idx_negotiation_log_session ON negotiation_log(session_id);
CREATE INDEX idx_negotiation_log_version ON negotiation_log(version_id);
CREATE INDEX idx_negotiation_log_timestamp ON negotiation_log(timestamp DESC);
CREATE INDEX idx_negotiation_log_status ON negotiation_log(status);

-- ============================================================================
-- POLICIES AND PLAYBOOKS
-- ============================================================================

CREATE TABLE policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(organization_id),
    policy_identifier VARCHAR(100) UNIQUE NOT NULL, -- Human-readable ID
    policy_title TEXT NOT NULL,
    policy_text TEXT NOT NULL,
    policy_version VARCHAR(50) NOT NULL,
    policy_category VARCHAR(100), -- e.g., "liability", "ip", "termination"
    effective_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_system VARCHAR(100), -- e.g., "Help Desk"
    embedding_vector VECTOR(1536), -- For semantic search (requires pgvector extension)
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_policies_org ON policies(organization_id);
CREATE INDEX idx_policies_identifier ON policies(policy_identifier);
CREATE INDEX idx_policies_category ON policies(policy_category);

CREATE TABLE playbook_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID REFERENCES policies(policy_id) ON DELETE CASCADE,
    rule_text TEXT NOT NULL,
    rule_type VARCHAR(100), -- e.g., "required_clause", "value_constraint", "prohibited_term"
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    allows_alternatives BOOLEAN DEFAULT FALSE,
    alternative_conditions JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_playbook_rules_policy ON playbook_rules(policy_id);
CREATE INDEX idx_playbook_rules_severity ON playbook_rules(severity);

-- ============================================================================
-- FINDINGS AND RATIONALE (REQ-DR-001 to REQ-DR-005)
-- ============================================================================

CREATE TABLE findings (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES document_versions(version_id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses(clause_id) ON DELETE SET NULL,
    policy_id UUID REFERENCES policies(policy_id),
    rule_id UUID REFERENCES playbook_rules(rule_id),
    issue_type VARCHAR(100) NOT NULL CHECK (issue_type IN ('deviation', 'risk', 'compliance', 'missing_clause')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    evidence_quote TEXT,
    policy_requirement TEXT,
    suggested_edit TEXT,
    provenance JSONB NOT NULL, -- REQ-DR-005: retrieval sources, model version, timestamps
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_provenance CHECK (
        jsonb_typeof(provenance) = 'object' AND
        provenance ? 'model_version' AND
        provenance ? 'analysis_timestamp'
    ),
    CONSTRAINT high_severity_requires_evidence CHECK (
        severity NOT IN ('high', 'critical') OR
        (evidence_quote IS NOT NULL AND policy_id IS NOT NULL)
    )
);

CREATE INDEX idx_findings_version ON findings(version_id);
CREATE INDEX idx_findings_clause ON findings(clause_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_issue_type ON findings(issue_type);

-- ============================================================================
-- NEUTRAL RATIONALE (REQ-NR-001 to REQ-NR-005)
-- ============================================================================

CREATE TABLE neutral_rationale (
    rationale_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
    schema_version VARCHAR(10) DEFAULT '1.0',
    neutral_explanation TEXT NOT NULL,
    proposed_change JSONB NOT NULL,
    fallback_options JSONB DEFAULT '[]'::jsonb,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_proposed_change CHECK (
        jsonb_typeof(proposed_change) = 'object' AND
        proposed_change ? 'change_type' AND
        proposed_change ? 'proposed' AND
        proposed_change ? 'reasoning'
    ),
    CONSTRAINT valid_fallback_options CHECK (
        jsonb_typeof(fallback_options) = 'array'
    )
);

CREATE INDEX idx_rationale_finding ON neutral_rationale(finding_id);

-- ============================================================================
-- PERSONALITY TRANSFORMATIONS (REQ-PA-001 to REQ-PA-008)
-- ============================================================================

CREATE TABLE rationale_transformations (
    transformation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rationale_id UUID NOT NULL REFERENCES neutral_rationale(rationale_id) ON DELETE CASCADE,
    style_params JSONB NOT NULL,
    transformed_text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cache_ttl TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '1 hour'),
    CONSTRAINT valid_style_params CHECK (
        jsonb_typeof(style_params) = 'object' AND
        style_params ? 'tone' AND
        style_params ? 'formality' AND
        style_params ? 'aggressiveness' AND
        style_params ? 'audience'
    )
);

CREATE INDEX idx_transformations_rationale ON rationale_transformations(rationale_id);
CREATE INDEX idx_transformations_cache ON rationale_transformations(cache_ttl);

-- ============================================================================
-- SUGGESTED EDITS (REQ-SE-001 to REQ-SE-006)
-- ============================================================================

CREATE TABLE suggested_edits (
    edit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES document_versions(version_id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses(clause_id) ON DELETE SET NULL,
    finding_id UUID REFERENCES findings(finding_id),
    edit_type VARCHAR(50) CHECK (edit_type IN ('insertion', 'deletion', 'replacement')),
    char_start INTEGER,
    char_end INTEGER,
    original_text TEXT,
    suggested_text TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'modified', 'superseded')),
    modified_text TEXT, -- If status = 'modified'
    modification_rationale TEXT,
    policy_reference UUID REFERENCES policies(policy_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(user_id)
);

CREATE INDEX idx_edits_version ON suggested_edits(version_id);
CREATE INDEX idx_edits_clause ON suggested_edits(clause_id);
CREATE INDEX idx_edits_status ON suggested_edits(status);

-- ============================================================================
-- REJECTION BLOCKLIST (REQ-VC-006)
-- ============================================================================

CREATE TABLE rejected_clauses (
    rejection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES negotiation_sessions(session_id) ON DELETE CASCADE,
    clause_text TEXT NOT NULL,
    rejection_rationale TEXT NOT NULL,
    rejecting_party VARCHAR(50) CHECK (rejecting_party IN ('internal', 'counterparty')),
    rejected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rejected_by UUID REFERENCES users(user_id),
    embedding_vector VECTOR(1536), -- For semantic similarity search
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_rejected_clauses_session ON rejected_clauses(session_id);

-- ============================================================================
-- COUNTERPARTY INTELLIGENCE (REQ-CI-001)
-- ============================================================================

CREATE TABLE counterparties (
    counterparty_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    organization_type VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE counterparty_profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    counterparty_id UUID NOT NULL REFERENCES counterparties(counterparty_id) ON DELETE CASCADE,
    contract_count INTEGER DEFAULT 0,
    typical_positions JSONB DEFAULT '{}'::jsonb,
    common_concessions JSONB DEFAULT '[]'::jsonb,
    avg_cycle_time_days DECIMAL(5,2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT minimum_contracts_for_profile CHECK (contract_count >= 3)
);

CREATE INDEX idx_counterparty_profiles_counterparty ON counterparty_profiles(counterparty_id);

-- ============================================================================
-- OBLIGATION TRACKING (REQ-OE-001)
-- ============================================================================

CREATE TABLE obligations (
    obligation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES negotiation_sessions(session_id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses(clause_id) ON DELETE SET NULL,
    responsible_party VARCHAR(50) CHECK (responsible_party IN ('internal', 'counterparty', 'both')),
    action_description TEXT NOT NULL,
    deadline DATE,
    deadline_text VARCHAR(255), -- Original text like "within 30 days"
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'overdue', 'waived')),
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_obligations_session ON obligations(session_id);
CREATE INDEX idx_obligations_deadline ON obligations(deadline);
CREATE INDEX idx_obligations_status ON obligations(status);

-- ============================================================================
-- POLICY DRIFT DETECTION (REQ-PD-001)
-- ============================================================================

CREATE TABLE drift_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID NOT NULL REFERENCES policies(policy_id),
    policy_version_new VARCHAR(50) NOT NULL,
    policy_version_playbook VARCHAR(50) NOT NULL,
    drift_score DECIMAL(4,3) CHECK (drift_score >= 0 AND drift_score <= 1), -- Cosine similarity
    affected_rules JSONB DEFAULT '[]'::jsonb,
    recommended_action TEXT,
    alert_status VARCHAR(50) DEFAULT 'open' CHECK (alert_status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_by UUID REFERENCES users(user_id),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_drift_alerts_policy ON drift_alerts(policy_id);
CREATE INDEX idx_drift_alerts_status ON drift_alerts(alert_status);

-- ============================================================================
-- EXCEPTION MINING (REQ-EM-001)
-- ============================================================================

CREATE TABLE exception_patterns (
    pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exception_cluster_id INTEGER,
    suggested_rule_text TEXT NOT NULL,
    supporting_exceptions JSONB DEFAULT '[]'::jsonb, -- Array of exception IDs
    frequency INTEGER DEFAULT 0,
    recommendation_confidence DECIMAL(3,2),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'implemented')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by UUID REFERENCES users(user_id),
    reviewed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_exception_patterns_status ON exception_patterns(status);

-- ============================================================================
-- AUDIT TRAIL
-- ============================================================================

CREATE TABLE audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    request_data JSONB,
    response_status INTEGER
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Version lineage view
CREATE VIEW version_lineage AS
WITH RECURSIVE lineage AS (
    SELECT
        version_id,
        session_id,
        parent_version_id,
        version_number,
        timestamp,
        source,
        1 as depth,
        ARRAY[version_id] as path
    FROM document_versions
    WHERE parent_version_id IS NULL

    UNION ALL

    SELECT
        dv.version_id,
        dv.session_id,
        dv.parent_version_id,
        dv.version_number,
        dv.timestamp,
        dv.source,
        l.depth + 1,
        l.path || dv.version_id
    FROM document_versions dv
    INNER JOIN lineage l ON dv.parent_version_id = l.version_id
)
SELECT * FROM lineage;

-- High-risk findings summary
CREATE VIEW high_risk_findings AS
SELECT
    f.finding_id,
    f.version_id,
    dv.session_id,
    ns.contract_name,
    f.clause_id,
    c.clause_identifier,
    f.severity,
    f.issue_type,
    f.evidence_quote,
    p.policy_identifier,
    nr.neutral_explanation,
    f.timestamp
FROM findings f
INNER JOIN document_versions dv ON f.version_id = dv.version_id
INNER JOIN negotiation_sessions ns ON dv.session_id = ns.session_id
LEFT JOIN clauses c ON f.clause_id = c.clause_id
LEFT JOIN policies p ON f.policy_id = p.policy_id
LEFT JOIN neutral_rationale nr ON f.finding_id = nr.finding_id
WHERE f.severity IN ('high', 'critical');

-- Upcoming obligations view
CREATE VIEW upcoming_obligations AS
SELECT
    o.obligation_id,
    o.session_id,
    ns.contract_name,
    o.responsible_party,
    o.action_description,
    o.deadline,
    o.status,
    (o.deadline - CURRENT_DATE) as days_until_due
FROM obligations o
INNER JOIN negotiation_sessions ns ON o.session_id = ns.session_id
WHERE o.status = 'pending'
  AND o.deadline >= CURRENT_DATE
ORDER BY o.deadline;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON negotiation_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-increment version numbers
CREATE OR REPLACE FUNCTION set_version_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.version_number IS NULL THEN
        SELECT COALESCE(MAX(version_number), 0) + 1
        INTO NEW.version_number
        FROM document_versions
        WHERE session_id = NEW.session_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_version_number_trigger BEFORE INSERT ON document_versions
    FOR EACH ROW EXECUTE FUNCTION set_version_number();

-- Update current_version_id in session
CREATE OR REPLACE FUNCTION update_session_current_version()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE negotiation_sessions
    SET current_version_id = NEW.version_id,
        updated_at = NOW()
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_current_version_trigger AFTER INSERT ON document_versions
    FOR EACH ROW EXECUTE FUNCTION update_session_current_version();

-- Log edit status changes
CREATE OR REPLACE FUNCTION log_edit_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO negotiation_log (
            session_id,
            version_id,
            clause_id,
            change_type,
            before_state,
            after_state,
            source,
            status
        )
        SELECT
            dv.session_id,
            NEW.version_id,
            NEW.clause_id,
            'status_change',
            jsonb_build_object('status', OLD.status, 'edit_id', NEW.edit_id),
            jsonb_build_object('status', NEW.status, 'edit_id', NEW.edit_id),
            'internal',
            NEW.status
        FROM document_versions dv
        WHERE dv.version_id = NEW.version_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_edit_status_trigger AFTER UPDATE ON suggested_edits
    FOR EACH ROW EXECUTE FUNCTION log_edit_status_change();

-- ============================================================================
-- RBAC FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id UUID,
    p_action VARCHAR,
    p_resource_type VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    user_role VARCHAR;
BEGIN
    SELECT role INTO user_role FROM users WHERE user_id = p_user_id;

    -- Admin has all permissions
    IF user_role = 'admin' THEN
        RETURN TRUE;
    END IF;

    -- Permission matrix
    IF p_action = 'read' THEN
        RETURN user_role IN ('viewer', 'reviewer', 'editor', 'approver', 'admin');
    ELSIF p_action = 'comment' THEN
        RETURN user_role IN ('reviewer', 'editor', 'approver', 'admin');
    ELSIF p_action = 'edit' THEN
        RETURN user_role IN ('editor', 'approver', 'admin');
    ELSIF p_action = 'approve' THEN
        RETURN user_role IN ('approver', 'admin');
    ELSIF p_action = 'rollback' THEN
        RETURN user_role IN ('admin');
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA INSERTION FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION create_sample_organization() RETURNS UUID AS $$
DECLARE
    new_org_id UUID;
BEGIN
    INSERT INTO organizations (name, default_style_params)
    VALUES ('Acme Legal Corp', '{
        "tone": "verbose",
        "formality": "legal",
        "aggressiveness": "strict",
        "audience": "internal"
    }'::jsonb)
    RETURNING organization_id INTO new_org_id;

    RETURN new_org_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Partial indexes for common queries
CREATE INDEX idx_active_sessions ON negotiation_sessions(session_id)
    WHERE status = 'active';

CREATE INDEX idx_pending_edits ON suggested_edits(version_id, status)
    WHERE status = 'pending';

CREATE INDEX idx_critical_findings ON findings(version_id, severity)
    WHERE severity = 'critical';

-- ============================================================================
-- DATABASE COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE document_versions IS 'REQ-VC-001: Version creation with UUID + timestamp';
COMMENT ON TABLE annotations IS 'REQ-VC-002: Comment & redline preservation with clause anchoring';
COMMENT ON TABLE negotiation_log IS 'REQ-VC-004: Consolidated audit trail for all changes';
COMMENT ON TABLE neutral_rationale IS 'REQ-NR-001 to REQ-NR-005: Neutral ground truth rationale storage';
COMMENT ON TABLE rationale_transformations IS 'REQ-PA-001 to REQ-PA-008: Personality-transformed rationale cache';
COMMENT ON TABLE findings IS 'REQ-DR-001 to REQ-DR-005: Structured findings with provenance';
COMMENT ON TABLE suggested_edits IS 'REQ-SE-001 to REQ-SE-006: Track-change format edits with status';
COMMENT ON TABLE drift_alerts IS 'REQ-PD-001: Policy drift detection alerts';
COMMENT ON TABLE obligations IS 'REQ-OE-001: Obligation extraction and tracking';
COMMENT ON TABLE counterparty_profiles IS 'REQ-CI-001: Counterparty intelligence profiles';
COMMENT ON TABLE exception_patterns IS 'REQ-EM-001: Exception mining for playbook evolution';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
