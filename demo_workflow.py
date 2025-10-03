"""
Complete End-to-End Demo: Contract Analysis Workflow

This demo shows the full 4-agent pipeline in action:
1. Diligent Reviewer → finds policy deviations
2. Neutral Rationale → generates objective explanations
3. Personality Agent → transforms based on style
4. Editor Agent → creates track-change edits

Prerequisites:
- ANTHROPIC_API_KEY environment variable set
- legal_assistant.db created (run setup_sqlite.py first)
- Your clause extraction service (simulated here)

Usage:
    export ANTHROPIC_API_KEY="your-key-here"
    python3 demo_workflow.py
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import workflow and policy helper
from src.agents.workflow import analyze_contract
from get_policies import get_policies_for_contract


# =============================================================================
# SAMPLE CONTRACT (SaaS Agreement)
# =============================================================================

SAMPLE_CONTRACT = """
SOFTWARE AS A SERVICE AGREEMENT

This Software as a Service Agreement ("Agreement") is entered into as of January 1, 2025
("Effective Date") by and between TechVendor Inc. ("Provider") and Customer Corp. ("Customer").

1. SERVICE LEVEL AGREEMENT
   Provider shall use commercially reasonable efforts to maintain the Service.
   The Service shall be available 99.5% of the time during each calendar month.
   No service credits or refunds will be provided for downtime.

2. LIMITATION OF LIABILITY
   In no event shall Provider's total liability exceed the total fees paid by
   Customer in the twelve (12) month period preceding the claim, regardless of
   the form of action. Provider shall have no liability for any indirect, special,
   incidental, or consequential damages.

3. DATA PROTECTION
   Provider will process Customer data in accordance with applicable laws.
   Parties agree to negotiate a Data Processing Addendum if required.

4. GOVERNING LAW
   This Agreement shall be governed by the laws of the State of Delaware, USA,
   without regard to its conflict of law provisions.

5. INTELLECTUAL PROPERTY INDEMNITY
   Provider will defend Customer against claims that the Service infringes
   third-party intellectual property rights, provided Customer notifies Provider
   promptly of such claims.

6. PAYMENT TERMS
   Customer shall pay all fees within sixty (60) days of invoice date.
   Late payments may incur interest charges.
"""


# =============================================================================
# SIMULATED CLAUSE EXTRACTION
# (In production, this comes from your extraction service)
# =============================================================================

def extract_clauses(contract_text: str) -> List[Dict]:
    """
    Simulate clause extraction service

    In production, replace with your actual extraction service:
        from your_extraction_service import extract_clauses

    Returns:
        List of clause dicts with clause_id, clause_text, clause_type
    """

    # Simulated extraction (in reality, use NLP/pattern matching)
    clauses = [
        {
            'clause_id': 'clause-001',
            'clause_text': 'Provider shall use commercially reasonable efforts to maintain the Service. The Service shall be available 99.5% of the time during each calendar month. No service credits or refunds will be provided for downtime.',
            'clause_type': 'service_levels',
            'clause_identifier': 'Section 1',
            'char_start': 280,
            'char_end': 480
        },
        {
            'clause_id': 'clause-002',
            'clause_text': "In no event shall Provider's total liability exceed the total fees paid by Customer in the twelve (12) month period preceding the claim, regardless of the form of action.",
            'clause_type': 'limitation_of_liability',
            'clause_identifier': 'Section 2',
            'char_start': 520,
            'char_end': 690
        },
        {
            'clause_id': 'clause-003',
            'clause_text': 'Provider will process Customer data in accordance with applicable laws. Parties agree to negotiate a Data Processing Addendum if required.',
            'clause_type': 'data_protection',
            'clause_identifier': 'Section 3',
            'char_start': 850,
            'char_end': 990
        },
        {
            'clause_id': 'clause-004',
            'clause_text': 'This Agreement shall be governed by the laws of the State of Delaware, USA, without regard to its conflict of law provisions.',
            'clause_type': 'governing_law',
            'clause_identifier': 'Section 4',
            'char_start': 1020,
            'char_end': 1145
        },
        {
            'clause_id': 'clause-005',
            'clause_text': 'Provider will defend Customer against claims that the Service infringes third-party intellectual property rights, provided Customer notifies Provider promptly of such claims.',
            'clause_type': 'indemnity',
            'clause_identifier': 'Section 5',
            'char_start': 1200,
            'char_end': 1375
        },
        {
            'clause_id': 'clause-006',
            'clause_text': 'Customer shall pay all fees within sixty (60) days of invoice date. Late payments may incur interest charges.',
            'clause_type': 'payment_terms',
            'clause_identifier': 'Section 6',
            'char_start': 1400,
            'char_end': 1510
        }
    ]

    return clauses


# =============================================================================
# MAIN DEMO
# =============================================================================

async def run_demo():
    """Run complete contract analysis workflow"""

    print("\n" + "="*100)
    print("CONTRACT ANALYSIS WORKFLOW DEMO")
    print("="*100 + "\n")

    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ ERROR: ANTHROPIC_API_KEY not set")
        print("\nPlease run:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return

    print("✅ ANTHROPIC_API_KEY found\n")

    # Step 1: Load policies
    print("📋 STEP 1: Loading Policies and Playbook Rules")
    print("-" * 100)

    policies = get_policies_for_contract(
        contract_type='saas',
        model_orientation='buy'  # We're the customer buying SaaS
    )

    print(f"Loaded {len(policies)} applicable policies:")
    for i, policy in enumerate(policies, 1):
        source = policy['source']
        severity = policy['severity_default']
        text = policy['policy_text'][:80]
        print(f"  {i}. [{severity.upper():8s}] [{source:15s}] {text}...")

    # Step 2: Extract clauses
    print(f"\n📄 STEP 2: Extracting Clauses from Contract")
    print("-" * 100)

    clauses = extract_clauses(SAMPLE_CONTRACT)

    print(f"Extracted {len(clauses)} clauses:")
    for clause in clauses:
        clause_type = clause['clause_type']
        text = clause['clause_text'][:80]
        print(f"  - {clause['clause_identifier']:15s} [{clause_type:30s}] {text}...")

    # Step 3: Run analysis workflow
    print(f"\n🤖 STEP 3: Running 4-Agent Analysis Pipeline")
    print("-" * 100)
    print("This will take ~30-60 seconds as each agent processes the contract...\n")

    start_time = datetime.now()

    # Configure personality (style parameters)
    style_params = {
        'tone': 'concise',           # concise | balanced | verbose
        'formality': 'legal',        # legal | plain_english
        'aggressiveness': 'strict',  # strict | balanced | flexible
        'audience': 'internal'       # internal | counterparty
    }

    print(f"Style Configuration:")
    print(f"  - Tone: {style_params['tone']}")
    print(f"  - Formality: {style_params['formality']}")
    print(f"  - Aggressiveness: {style_params['aggressiveness']}")
    print(f"  - Audience: {style_params['audience']}\n")

    # Run the workflow (disable checkpointing for demo)
    from src.agents.workflow import ContractAnalysisWorkflow
    workflow = ContractAnalysisWorkflow(enable_checkpointing=False)

    result = await workflow.analyze_contract(
        version_id="demo-v1",
        session_id="demo-session-1",
        contract_text=SAMPLE_CONTRACT,
        clauses=clauses,
        policies=policies,
        style_params=style_params
    )

    duration = (datetime.now() - start_time).total_seconds()

    print(f"✅ Analysis complete in {duration:.1f} seconds\n")

    # Step 4: Display results
    print("📊 STEP 4: Analysis Results")
    print("=" * 100)

    summary = result['analysis_summary']
    findings = result['findings']
    rationales = result['neutral_rationales']
    transformations = result['transformed_rationales']
    edits = result['suggested_edits']

    # Summary statistics
    print(f"\n📈 Summary Statistics:")
    print(f"  - Total Findings: {summary['total_findings']}")
    print(f"  - Critical Issues: {summary['critical_count']}")
    print(f"  - High Priority Issues: {summary['high_count']}")
    print(f"  - Suggested Edits: {summary['total_edits']}")
    print(f"  - Edits with Conflicts: {summary['edits_with_conflicts']}")

    print(f"\n  Findings by Severity:")
    for severity, count in summary['by_severity'].items():
        print(f"    - {severity.upper():8s}: {count}")

    # Detailed findings
    if findings:
        print(f"\n\n🔍 DETAILED FINDINGS:")
        print("-" * 100)

        for i, finding in enumerate(findings, 1):
            print(f"\n{i}. [{finding['severity'].upper()}] {finding['deviation_type'].replace('_', ' ').title()}")
            print(f"   Policy: {finding['policy_id']}")
            print(f"   Evidence: \"{finding['evidence_quote'][:100]}...\"")
            print(f"   Explanation: {finding['explanation']}")

    # Neutral rationales
    if rationales:
        print(f"\n\n📝 NEUTRAL RATIONALES:")
        print("-" * 100)

        for i, rationale in enumerate(rationales, 1):
            print(f"\n{i}. Rationale ID: {rationale['rationale_id'][:8]}...")
            print(f"   Explanation: {rationale['neutral_explanation']}")
            print(f"   Proposed Change Type: {rationale['proposed_change']['change_type']}")
            print(f"   Proposed: {rationale['proposed_change']['proposed'][:100]}...")

            if rationale.get('fallback_options'):
                print(f"   Fallback Options: {len(rationale['fallback_options'])} available")

    # Styled transformations
    if transformations:
        print(f"\n\n🎨 STYLED TRANSFORMATIONS (Personality Agent Output):")
        print("-" * 100)
        print(f"Style: {style_params['tone']} + {style_params['aggressiveness']} + {style_params['audience']}\n")

        for i, transformation in enumerate(transformations[:3], 1):  # Show first 3
            print(f"\n{i}. {transformation['transformed_text']}")

    # Suggested edits
    if edits:
        print(f"\n\n✏️  SUGGESTED EDITS (Track Changes Format):")
        print("-" * 100)

        for i, edit in enumerate(edits, 1):
            print(f"\n{i}. Edit ID: {edit['edit_id'][:8]}... | Type: {edit['edit_type']}")
            print(f"   Summary: {edit['change_summary']}")
            print(f"   Status: {edit['status'].upper()}")

            if edit.get('conflicts_with'):
                print(f"   ⚠️  CONFLICTS WITH: {len(edit['conflicts_with'])} other edit(s)")

            # Show deletions
            if edit.get('deletions'):
                print(f"   Deletions:")
                for deletion in edit['deletions'][:2]:  # First 2
                    print(f"     - Remove: \"{deletion['deleted_text'][:60]}...\"")

            # Show insertions
            if edit.get('insertions'):
                print(f"   Insertions:")
                for insertion in edit['insertions'][:2]:  # First 2
                    print(f"     - Add: \"{insertion['inserted_text'][:60]}...\"")

            print(f"   Policy Anchor: {edit['policy_anchor']['policy_id']} ({edit['policy_anchor']['severity']})")

    # Comparison: Neutral vs Styled
    print(f"\n\n🔀 COMPARISON: Neutral vs Styled Output")
    print("=" * 100)

    if rationales and transformations:
        # Take first example
        neutral = rationales[0]['neutral_explanation']
        styled = transformations[0]['transformed_text']

        print(f"\nNeutral (Objective, No Tone):")
        print(f"  {neutral}\n")

        print(f"Styled ({style_params['tone']} + {style_params['aggressiveness']} + {style_params['audience']}):")
        print(f"  {styled}\n")

    # Errors (if any)
    if result.get('errors'):
        print(f"\n⚠️  ERRORS ENCOUNTERED:")
        print("-" * 100)
        for error in result['errors']:
            print(f"  - {error}")

    print("\n" + "="*100)
    print("DEMO COMPLETE")
    print("="*100 + "\n")

    # Next steps
    print("🎯 Next Steps:")
    print("  1. Integrate your actual clause extraction service")
    print("  2. Adjust style_params for different communication modes")
    print("  3. Implement accept/reject workflow for suggested edits")
    print("  4. Export redline documents (HTML/Word)")
    print("  5. Store results in database for version tracking")
    print("\n📚 Key Files:")
    print("  - src/agents/workflow.py - Main orchestrator")
    print("  - get_policies.py - Policy loader")
    print("  - legal_assistant.db - Policy database")
    print("  - src/agents/*.py - Individual agents\n")


# =============================================================================
# STREAMING DEMO (Optional)
# =============================================================================

async def run_streaming_demo():
    """Demo with real-time updates as each agent completes"""

    print("\n" + "="*100)
    print("STREAMING WORKFLOW DEMO (Real-time Updates)")
    print("="*100 + "\n")

    from src.agents.workflow import ContractAnalysisWorkflow

    # Load data
    policies = get_policies_for_contract(contract_type='saas', model_orientation='buy')
    clauses = extract_clauses(SAMPLE_CONTRACT)

    # Create workflow
    workflow = ContractAnalysisWorkflow(enable_checkpointing=False)

    # Stream execution
    print("🔄 Streaming execution...\n")

    async for update in workflow.analyze_contract_streaming(
        version_id="demo-v1",
        session_id="demo-session-1",
        contract_text=SAMPLE_CONTRACT,
        clauses=clauses,
        policies=policies,
        style_params={'tone': 'concise', 'aggressiveness': 'strict', 'audience': 'internal'}
    ):
        node = update['node']
        stage = update['stage']
        findings = update['findings_count']
        rationales = update['rationales_count']
        edits = update['edits_count']

        print(f"✓ {node:20s} | Stage: {stage:15s} | Findings: {findings:2d} | Rationales: {rationales:2d} | Edits: {edits:2d}")

    print("\n✅ Streaming complete!\n")


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    import sys

    # Check if streaming mode requested
    if len(sys.argv) > 1 and sys.argv[1] == '--stream':
        asyncio.run(run_streaming_demo())
    else:
        asyncio.run(run_demo())
