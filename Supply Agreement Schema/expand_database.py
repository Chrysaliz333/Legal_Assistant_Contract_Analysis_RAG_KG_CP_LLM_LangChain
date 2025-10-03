"""
Expand Database with Comprehensive Policies and Playbook Rules

Adds 20+ new policies covering:
- Contract fundamentals
- Commercial terms
- Risk allocation
- Operational requirements
- Compliance requirements
"""

import sqlite3
import hashlib
from datetime import datetime

# Comprehensive policy expansion
EXPANDED_POLICIES = [
    # EXISTING (don't duplicate)
    # - limitation_of_liability (LP-401)
    # - governing_law (GL-101)
    # - data_protection (DP-104)

    # NEW POLICIES

    # ============================================================================
    # COMMERCIAL TERMS
    # ============================================================================
    {
        'policy_category': 'payment_terms',
        'policy_text': 'Payment terms must not exceed 30 days from invoice date for all vendor agreements. Extended payment terms (45-60 days) require CFO approval.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'pricing',
        'policy_text': 'All SaaS contracts must include price protection clauses limiting annual price increases to maximum 5% or CPI, whichever is lower.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'automatic_renewal',
        'policy_text': 'Automatic renewal clauses must include 90-day notice period for termination. Auto-renewal with less than 60 days notice is prohibited.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'minimum_commitment',
        'policy_text': 'Initial contract term must not exceed 3 years for new vendors. Multi-year commitments require procurement committee approval.',
        'severity_default': 'high'
    },

    # ============================================================================
    # RISK ALLOCATION
    # ============================================================================
    {
        'policy_category': 'indemnity',
        'policy_text': 'Vendor must provide full indemnity for third-party IP infringement claims, including duty to defend and reasonable attorneys\' fees.',
        'severity_default': 'critical'
    },
    {
        'policy_category': 'insurance',
        'policy_text': 'Vendors must maintain minimum insurance coverage: $2M general liability, $5M professional liability (E&O), $5M cyber liability for SaaS/data processors.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'warranty',
        'policy_text': 'Services must include warranties of (i) compliance with laws, (ii) professional workmanship, (iii) non-infringement of third-party rights. "As-is" clauses are prohibited.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'force_majeure',
        'policy_text': 'Force majeure clauses must not excuse payment obligations and must include termination rights after 30 consecutive days of service disruption.',
        'severity_default': 'medium'
    },

    # ============================================================================
    # OPERATIONAL REQUIREMENTS
    # ============================================================================
    {
        'policy_category': 'service_levels',
        'policy_text': 'SaaS agreements must include quantified SLAs with minimum 99.5% uptime for standard tier, 99.9% for business-critical systems.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'support',
        'policy_text': 'Support must include: (i) business hours email/portal support, (ii) 4-hour response time for critical issues, (iii) dedicated account manager for contracts >$100K annually.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'audit_rights',
        'policy_text': 'Company must retain audit rights for compliance verification, with 15 business days notice, during business hours, maximum once per year.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'change_control',
        'policy_text': 'Material changes to services require 90 days advance notice. Negative changes allow termination for convenience with pro-rata refund.',
        'severity_default': 'medium'
    },

    # ============================================================================
    # COMPLIANCE & GOVERNANCE
    # ============================================================================
    {
        'policy_category': 'data_residency',
        'policy_text': 'Personal data of EU subjects must be processed and stored exclusively within EU/EEA. UK data must remain in UK or adequate jurisdiction.',
        'severity_default': 'critical'
    },
    {
        'policy_category': 'subprocessors',
        'policy_text': 'DPA must include: (i) list of current subprocessors, (ii) 30-day notice for new subprocessors, (iii) objection rights with termination option.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'security',
        'policy_text': 'Vendors must maintain ISO 27001 or SOC 2 Type II certification. Annual security assessments must be provided upon request.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'breach_notification',
        'policy_text': 'Security breaches affecting Company data must be reported within 24 hours of discovery. Vendor must cooperate with incident response.',
        'severity_default': 'critical'
    },

    # ============================================================================
    # CONTRACT FUNDAMENTALS
    # ============================================================================
    {
        'policy_category': 'assignment',
        'policy_text': 'Vendor assignment requires Company consent (not to be unreasonably withheld). Company may assign freely to affiliates or in M&A transactions.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'termination_for_convenience',
        'policy_text': 'Company must retain termination for convenience right with 90-day notice (60 days for contracts <$50K annually) and pro-rata refund.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'termination_for_cause',
        'policy_text': 'Termination for cause must include material breach with 30-day cure period. Immediate termination for insolvency, criminal conduct, or regulatory violations.',
        'severity_default': 'high'
    },
    {
        'policy_category': 'dispute_resolution',
        'policy_text': 'Disputes must be resolved under English law with jurisdiction in England and Wales courts. Arbitration clauses require legal approval.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'confidentiality',
        'policy_text': 'Mutual confidentiality obligations with standard exceptions (public knowledge, independent development, required disclosure). 5-year term post-termination.',
        'severity_default': 'medium'
    },
    {
        'policy_category': 'intellectual_property',
        'policy_text': 'Company must own all deliverables, work product, and custom developments. Pre-existing vendor IP may be licensed with perpetual, irrevocable rights.',
        'severity_default': 'high'
    },
]

# Expanded playbook rules for specific scenarios
EXPANDED_PLAYBOOK_RULES = [
    # EXISTING (don't duplicate)
    # - SaaS SLA (99.9% uptime)
    # - IP indemnity

    # NEW PLAYBOOK RULES

    {
        'rule_text': 'For SaaS contracts, service credits must be at least 10% of monthly fees per 1% below SLA, capped at 50% of monthly fees. Credits must be automatic, not require claim.',
        'applicable_contract_types': ['saas', 'cloud'],
        'applicable_clauses': ['service_levels', 'remedies'],
        'severity_override': 'high',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'Cloud/SaaS contracts must include data portability provisions: (i) export in standard format, (ii) available on termination, (iii) 90-day post-termination access.',
        'applicable_contract_types': ['saas', 'cloud', 'data_processing'],
        'applicable_clauses': ['data_protection', 'termination'],
        'severity_override': 'high',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'For professional services, deliverable acceptance criteria must be defined. Rejection rights within 10 business days with specific deficiency notice.',
        'applicable_contract_types': ['professional_services', 'consulting'],
        'applicable_clauses': ['deliverables', 'acceptance'],
        'severity_override': 'medium',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'Software licenses must be perpetual or include source code escrow for business-critical systems. Subscription-only requires redundancy plan.',
        'applicable_contract_types': ['software_license', 'saas'],
        'applicable_clauses': ['license_grant', 'business_continuity'],
        'severity_override': 'high',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'For contracts involving AI/ML: (i) training data ownership clarified, (ii) model bias testing commitment, (iii) explainability for high-risk decisions.',
        'applicable_contract_types': ['saas', 'software_license', 'ai_services'],
        'applicable_clauses': ['intellectual_property', 'data_protection', 'performance'],
        'severity_override': 'high',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'API-dependent integrations must include: (i) API stability commitment, (ii) 12-month deprecation notice, (iii) migration support for breaking changes.',
        'applicable_contract_types': ['saas', 'cloud', 'integration'],
        'applicable_clauses': ['technical_requirements', 'change_control'],
        'severity_override': 'medium',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'Volume discounts must include MFN (most favored nation) clause: if vendor offers better pricing to comparable customer, Company receives same benefit.',
        'applicable_contract_types': ['saas', 'software_license'],
        'applicable_clauses': ['pricing', 'fees'],
        'severity_override': 'medium',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'For disaster recovery: RTO (Recovery Time Objective) ≤ 4 hours, RPO (Recovery Point Objective) ≤ 1 hour for business-critical systems.',
        'applicable_contract_types': ['saas', 'cloud', 'infrastructure'],
        'applicable_clauses': ['service_levels', 'business_continuity'],
        'severity_override': 'critical',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'Open source components must be disclosed. GPL/AGPL licenses prohibited without legal review. Permissive licenses (MIT, Apache 2.0) acceptable.',
        'applicable_contract_types': ['software_license', 'saas', 'professional_services'],
        'applicable_clauses': ['intellectual_property', 'license_grant'],
        'severity_override': 'high',
        'model_orientation': 'buy'
    },
    {
        'rule_text': 'Benchmark/performance testing must be permitted. No-benchmark clauses require CTO approval and must allow anonymous publication of results.',
        'applicable_contract_types': ['saas', 'software_license', 'cloud'],
        'applicable_clauses': ['restrictions', 'confidentiality'],
        'severity_override': 'low',
        'model_orientation': 'buy'
    },
]


def generate_policy_id(policy_text):
    """Generate deterministic policy ID from text"""
    return hashlib.md5(policy_text.encode()).hexdigest()


def expand_database(db_path='legal_assistant.db'):
    """Add expanded policies and playbook rules to database"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add new policies
    policies_added = 0
    for policy in EXPANDED_POLICIES:
        policy_id = generate_policy_id(policy['policy_text'])

        try:
            cursor.execute("""
                INSERT INTO policies (policy_id, policy_text, policy_category, severity_default)
                VALUES (?, ?, ?, ?)
            """, (
                policy_id,
                policy['policy_text'],
                policy['policy_category'],
                policy['severity_default']
            ))
            policies_added += 1
            print(f"✅ Added policy: {policy['policy_category']}")
        except sqlite3.IntegrityError:
            print(f"⏭️  Skipped existing policy: {policy['policy_category']}")

    # Add new playbook rules
    rules_added = 0
    for rule in EXPANDED_PLAYBOOK_RULES:
        rule_id = generate_policy_id(rule['rule_text'])

        try:
            cursor.execute("""
                INSERT INTO playbook_rules (
                    rule_text, applicable_contract_types,
                    applicable_clauses, severity_override, model_orientation
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                rule['rule_text'],
                ','.join(rule['applicable_contract_types']),
                ','.join(rule['applicable_clauses']),
                rule['severity_override'],
                rule['model_orientation']
            ))
            rules_added += 1
            print(f"✅ Added playbook rule for: {', '.join(rule['applicable_clauses'])}")
        except sqlite3.IntegrityError:
            print(f"⏭️  Skipped existing rule for: {', '.join(rule['applicable_clauses'])}")

    conn.commit()
    conn.close()

    print(f"\n📊 Database Expansion Summary:")
    print(f"   - Policies added: {policies_added}")
    print(f"   - Playbook rules added: {rules_added}")
    print(f"   - Total policies: {policies_added + 3} (3 existing)")
    print(f"   - Total rules: {rules_added + 6} (6 existing)")

    return policies_added, rules_added


if __name__ == "__main__":
    expand_database()
