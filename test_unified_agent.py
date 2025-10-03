"""
Test script comparing old multi-agent vs new unified agent
"""

import asyncio
import json
from src.agents.unified_agent import UnifiedContractAgent
from get_policies import get_all_policies

async def main():
    print("=" * 80)
    print("UNIFIED AGENT TEST")
    print("=" * 80)

    # Sample contract with clear violations
    contract_text = """
    MASTER SERVICES AGREEMENT

    1. LIMITATION OF LIABILITY
    Contractor's total liability under this Agreement shall not exceed the amount
    of fees paid by Client in the twelve (12) months preceding the claim.

    2. INTELLECTUAL PROPERTY
    All work product created by Contractor shall remain the property of Contractor.
    Client is granted a non-exclusive, revocable license to use the work product.

    3. TERMINATION
    Either party may terminate this Agreement with thirty (30) days written notice.
    Upon termination, Client shall pay all outstanding fees within ninety (90) days.

    4. CONFIDENTIALITY
    Each party agrees to maintain confidentiality of the other party's information
    for a period of two (2) years following disclosure.
    """

    # Load policies
    all_policies = get_all_policies()

    # Convert to simpler format for unified agent
    policies = []
    for p in all_policies:
        policies.append({
            'policy_id': p['policy_id'],
            'title': p.get('policy_category', 'General Policy'),
            'requirement': p['policy_text']
        })

    print(f"\nContract length: {len(contract_text)} characters")
    print(f"Policies to check: {len(policies)}")
    print("\nPolicies:")
    for p in policies[:5]:
        print(f"  - {p['policy_id']}: {p['title']}")

    # Test with different personalities
    print("\n" + "=" * 80)
    print("TEST 1: Strict + Legal + Internal")
    print("=" * 80)

    agent_strict = UnifiedContractAgent(style_params={
        'tone': 'concise',
        'formality': 'legal',
        'aggressiveness': 'strict',
        'audience': 'internal'
    })

    result_strict = await agent_strict.analyze_contract(contract_text, policies)

    print(f"\nFindings: {len(result_strict.get('findings', []))}")
    print(f"With edits: {sum(1 for f in result_strict.get('findings', []) if f.get('suggested_edit'))}")

    # Show first finding
    if result_strict.get('findings'):
        finding = result_strict['findings'][0]
        print(f"\nSample finding:")
        print(f"  Clause: {finding.get('clause_reference')}")
        print(f"  Policy: {finding.get('policy_violated')}")
        print(f"  Evidence: {finding.get('contract_evidence', '')[:100]}...")
        print(f"  Explanation: {finding.get('issue_explanation', '')[:200]}...")
        if finding.get('suggested_edit'):
            edit = finding['suggested_edit']
            print(f"  Edit: {edit.get('current_text', '')[:50]}... → {edit.get('proposed_text', '')[:50]}...")

    print("\n" + "=" * 80)
    print("TEST 2: Flexible + Plain English + Counterparty")
    print("=" * 80)

    agent_flexible = UnifiedContractAgent(style_params={
        'tone': 'balanced',
        'formality': 'plain_english',
        'aggressiveness': 'flexible',
        'audience': 'counterparty'
    })

    result_flexible = await agent_flexible.analyze_contract(contract_text, policies)

    print(f"\nFindings: {len(result_flexible.get('findings', []))}")
    print(f"With edits: {sum(1 for f in result_flexible.get('findings', []) if f.get('suggested_edit'))}")

    # Show first finding
    if result_flexible.get('findings'):
        finding = result_flexible['findings'][0]
        print(f"\nSample finding (same issue, different style):")
        print(f"  Clause: {finding.get('clause_reference')}")
        print(f"  Policy: {finding.get('policy_violated')}")
        print(f"  Evidence: {finding.get('contract_evidence', '')[:100]}...")
        print(f"  Explanation: {finding.get('issue_explanation', '')[:200]}...")
        if finding.get('suggested_edit'):
            edit = finding['suggested_edit']
            print(f"  Edit: {edit.get('current_text', '')[:50]}... → {edit.get('proposed_text', '')[:50]}...")

    # Save results
    with open('unified_test_strict.json', 'w') as f:
        json.dump(result_strict, f, indent=2)

    with open('unified_test_flexible.json', 'w') as f:
        json.dump(result_flexible, f, indent=2)

    print("\n" + "=" * 80)
    print("Results saved to:")
    print("  - unified_test_strict.json")
    print("  - unified_test_flexible.json")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
