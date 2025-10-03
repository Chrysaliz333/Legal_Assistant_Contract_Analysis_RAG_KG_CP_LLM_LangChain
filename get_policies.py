"""
Helper script to load policies and playbook rules for agent workflow

Usage:
    from get_policies import get_all_policies

    policies = get_all_policies()
    # Returns list of dicts ready for analyze_contract()
"""

import sqlite3
import json
from typing import List, Dict

DB_PATH = "legal_assistant.db"


def get_all_policies(model_orientation: str = None) -> List[Dict]:
    """
    Load all policies and playbook rules from database

    Args:
        model_orientation: Optional filter ('buy' or 'sell')

    Returns:
        List of policy dicts ready for agent workflow

    Example:
        >>> policies = get_all_policies(model_orientation='buy')
        >>> len(policies)
        6  # 3 general policies + 3 buy-side playbook rules
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    cursor = conn.cursor()

    policies = []

    # Load general policies (apply to all contracts)
    cursor.execute("""
        SELECT
            policy_id,
            policy_text,
            policy_category,
            severity_default
        FROM policies
    """)

    for row in cursor.fetchall():
        policies.append({
            'policy_id': row['policy_id'],
            'policy_text': row['policy_text'],
            'policy_category': row['policy_category'],
            'severity_default': row['severity_default'],
            'source': 'policy'
        })

    # Load playbook rules (optionally filtered by orientation)
    query = """
        SELECT
            rule_id,
            rule_text,
            applicable_contract_types,
            applicable_clauses,
            severity_override,
            conditions,
            model_orientation
        FROM playbook_rules
    """

    params = []
    if model_orientation:
        query += " WHERE model_orientation = ?"
        params.append(model_orientation)

    cursor.execute(query, params)

    for row in cursor.fetchall():
        # Parse fields - handle both JSON and comma-separated strings
        contract_types_raw = row['applicable_contract_types']
        if contract_types_raw:
            try:
                contract_types = json.loads(contract_types_raw)
            except json.JSONDecodeError:
                # Fallback: comma-separated string
                contract_types = [t.strip() for t in contract_types_raw.split(',')]
        else:
            contract_types = []

        clauses_raw = row['applicable_clauses']
        if clauses_raw:
            try:
                clauses = json.loads(clauses_raw)
            except json.JSONDecodeError:
                # Fallback: comma-separated string
                clauses = [c.strip() for c in clauses_raw.split(',')]
        else:
            clauses = []

        conditions_raw = row['conditions']
        if conditions_raw:
            try:
                conditions = json.loads(conditions_raw)
            except json.JSONDecodeError:
                conditions = {}
        else:
            conditions = {}

        # Use first applicable clause as category (for compatibility with agents)
        category = clauses[0] if clauses else None

        policies.append({
            'policy_id': row['rule_id'],
            'policy_text': row['rule_text'],
            'policy_category': category,
            'severity_default': row['severity_override'] or 'medium',
            'source': 'playbook_rule',
            'model_orientation': row['model_orientation'],
            'applicable_contract_types': contract_types,
            'applicable_clauses': clauses,
            'conditions': conditions
        })

    conn.close()

    return policies


def get_policies_for_contract(
    contract_type: str = None,
    model_orientation: str = None
) -> List[Dict]:
    """
    Get policies relevant to a specific contract type

    Args:
        contract_type: e.g., 'saas', 'msa', 'professional_services'
        model_orientation: 'buy' or 'sell'

    Returns:
        Filtered list of applicable policies

    Example:
        >>> policies = get_policies_for_contract(
        ...     contract_type='saas',
        ...     model_orientation='buy'
        ... )
    """
    all_policies = get_all_policies(model_orientation)

    if not contract_type:
        return all_policies

    # Filter playbook rules by contract type
    filtered = []

    for policy in all_policies:
        # Always include general policies
        if policy['source'] == 'policy':
            filtered.append(policy)
        # Include playbook rules that match contract type
        elif contract_type in policy.get('applicable_contract_types', []):
            filtered.append(policy)

    return filtered


def print_policies_summary():
    """Print summary of all policies in database"""

    policies = get_all_policies()

    print(f"\n{'='*80}")
    print(f"POLICIES AND PLAYBOOK RULES SUMMARY")
    print(f"{'='*80}\n")

    # Group by source
    general = [p for p in policies if p['source'] == 'policy']
    playbook = [p for p in policies if p['source'] == 'playbook_rule']

    print(f"📋 General Policies ({len(general)}):")
    for p in general:
        print(f"  [{p['severity_default'].upper():8s}] {p['policy_category']:30s} - {p['policy_text'][:80]}...")

    print(f"\n📖 Playbook Rules ({len(playbook)}):")
    buy_rules = [p for p in playbook if p['model_orientation'] == 'buy']
    sell_rules = [p for p in playbook if p['model_orientation'] == 'sell']

    print(f"\n  Buy-Side Rules ({len(buy_rules)}):")
    for p in buy_rules:
        types = ', '.join(p['applicable_contract_types'][:3])
        print(f"    [{p['severity_default'].upper():8s}] {types:30s} - {p['policy_text'][:60]}...")

    print(f"\n  Sell-Side Rules ({len(sell_rules)}):")
    for p in sell_rules:
        types = ', '.join(p['applicable_contract_types'][:3])
        print(f"    [{p['severity_default'].upper():8s}] {types:30s} - {p['policy_text'][:60]}...")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    # Demo usage
    print_policies_summary()

    print("\nExample: Get all buy-side policies for SaaS contract")
    saas_policies = get_policies_for_contract(
        contract_type='saas',
        model_orientation='buy'
    )
    print(f"Found {len(saas_policies)} applicable policies")
    for p in saas_policies[:3]:
        print(f"  - {p['policy_text'][:80]}...")
