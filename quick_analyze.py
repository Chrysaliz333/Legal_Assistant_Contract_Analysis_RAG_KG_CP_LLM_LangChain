"""
Quick Contract Analysis - Fast evaluation of legal output
Uses simple section extraction to get you results quickly
"""

import asyncio
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

from src.agents.workflow import ContractAnalysisWorkflow
from get_policies import get_policies_for_contract


def extract_clauses_simple(contract_text: str) -> List[Dict]:
    """
    Fast extraction using section headers
    Looks for patterns like "1.", "1.1", "SECTION 1", etc.
    """
    clauses = []

    # Common clause type mappings (keywords → clause_type)
    clause_patterns = {
        'service level|sla|uptime|availability': 'service_levels',
        'limitation of liability|liability cap': 'limitation_of_liability',
        'data protection|privacy|gdpr|dpa': 'data_protection',
        'governing law|jurisdiction|dispute': 'governing_law',
        'indemnity|indemnif': 'indemnity',
        'payment|fees|invoice': 'payment_terms',
        'termination|cancel': 'termination',
        'confidential': 'confidentiality',
        'intellectual property|ip rights': 'intellectual_property',
        'warrant': 'warranty',
        'insurance': 'insurance',
        'audit': 'audit_rights',
        'renewal|renew': 'automatic_renewal',
        'assignment|assign': 'assignment',
        'force majeure': 'force_majeure'
    }

    # Multiple patterns for different contract formats
    # Pattern 1: "1." or "1.1" at start of line
    # Pattern 2: "Section 1" or "Article 1"
    # Pattern 3: All caps headers like "GOVERNING LAW"
    section_patterns = [
        r'^\s*(\d+(?:\.\d+)?)[.\s]+(.+?)$',  # "1." or "1.1 Title"
        r'^\s*(Section|Article|Clause)\s+(\d+(?:\.\d+)?)[:\s]+(.+?)$',  # "Section 1: Title"
        r'^\s*([A-Z][A-Z\s]{3,})$'  # "GOVERNING LAW"
    ]

    lines = contract_text.split('\n')
    current_section = None
    current_text = []
    current_identifier = None

    for line in lines:
        matched = False
        match = None

        # Try each pattern
        for pattern in section_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                matched = True
                break

        if matched and match:
            # Save previous section
            if current_section and current_text:
                clause_text = '\n'.join(current_text).strip()
                if len(clause_text) > 20:  # Skip very short sections
                    # Classify clause type
                    clause_type = 'other'
                    for pattern, type_name in clause_patterns.items():
                        if re.search(pattern, current_section, re.IGNORECASE):
                            clause_type = type_name
                            break

                    clauses.append({
                        'clause_id': f'clause-{len(clauses) + 1}',
                        'clause_identifier': current_identifier,
                        'clause_type': clause_type,
                        'clause_text': clause_text
                    })

            # Start new section - handle different match groups
            groups = match.groups()
            if len(groups) >= 2:
                current_identifier = groups[0].strip() if groups[0] else f"Section {len(clauses)+1}"
                current_section = groups[-1].strip() if groups[-1] else groups[0].strip()
            else:
                current_identifier = groups[0].strip()
                current_section = groups[0].strip()
            current_text = [line]
        else:
            # Continue current section
            if current_section:
                current_text.append(line)

    # Save last section
    if current_section and current_text:
        clause_text = '\n'.join(current_text).strip()
        if len(clause_text) > 20:
            clause_type = 'other'
            for pattern, type_name in clause_patterns.items():
                if re.search(pattern, current_section, re.IGNORECASE):
                    clause_type = type_name
                    break

            clauses.append({
                'clause_id': f'clause-{len(clauses) + 1}',
                'clause_identifier': current_identifier,
                'clause_type': clause_type,
                'clause_text': clause_text
            })

    # Fallback: If no clauses found, split by double newlines (paragraphs)
    if not clauses:
        paragraphs = contract_text.split('\n\n')
        for i, para in enumerate(paragraphs, 1):
            para = para.strip()
            if len(para) > 50:  # Only meaningful paragraphs
                # Try to classify
                clause_type = 'other'
                for pattern, type_name in clause_patterns.items():
                    if re.search(pattern, para, re.IGNORECASE):
                        clause_type = type_name
                        break

                clauses.append({
                    'clause_id': f'clause-{i}',
                    'clause_identifier': f'Paragraph {i}',
                    'clause_type': clause_type,
                    'clause_text': para
                })

    return clauses


async def quick_analyze(file_path: str):
    """Quick analysis for legal output evaluation"""

    print("=" * 100)
    print("QUICK CONTRACT ANALYSIS - Legal Output Evaluation")
    print("=" * 100)
    print(f"📄 File: {file_path}\n")

    # Read file
    contract_text = Path(file_path).read_text()
    print(f"✅ Loaded contract ({len(contract_text)} characters)\n")

    # Extract clauses (simple pattern matching)
    print("🔍 Extracting clauses...")
    clauses = extract_clauses_simple(contract_text)
    print(f"✅ Found {len(clauses)} sections\n")

    for clause in clauses[:10]:
        print(f"  - Section {clause['clause_identifier']:6s} [{clause['clause_type']:25s}] {clause['clause_text'][:60]}...")
    if len(clauses) > 10:
        print(f"  ... and {len(clauses) - 10} more\n")

    # Load policies
    print("📚 Loading policies...")
    policies = get_policies_for_contract(contract_type='saas', model_orientation='buy')
    print(f"✅ Loaded {len(policies)} policies\n")

    # Run analysis
    print("🚀 Running 4-agent analysis...")
    print("This will take 60-120 seconds...\n")

    start_time = datetime.now()

    workflow = ContractAnalysisWorkflow(enable_checkpointing=False)

    result = await workflow.analyze_contract(
        version_id=f"quick-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        session_id=f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        contract_text=contract_text,
        clauses=clauses,
        policies=policies,
        style_params={
            'tone': 'concise',
            'formality': 'legal',
            'aggressiveness': 'strict',
            'audience': 'internal'
        }
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Analysis complete in {elapsed:.1f} seconds\n")

    # Display results
    print_results(result)

    return result


def print_results(result: Dict):
    """Print formatted results"""

    print("=" * 100)
    print("LEGAL ANALYSIS RESULTS")
    print("=" * 100)

    findings = result.get('findings', [])
    suggested_edits = result.get('suggested_edits', [])

    # Stats
    print(f"\n📊 SUMMARY")
    print(f"  Total Issues Found: {len(findings)}")

    by_severity = {}
    for f in findings:
        sev = f.get('severity', 'unknown').upper()
        by_severity[sev] = by_severity.get(sev, 0) + 1

    for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if sev in by_severity:
            print(f"    - {sev}: {by_severity[sev]}")

    print(f"  Suggested Edits: {len(suggested_edits)}")

    # Findings
    print(f"\n🔍 FINDINGS (Issues Identified)\n")
    print("-" * 100)

    for i, finding in enumerate(findings, 1):
        sev = finding.get('severity', 'unknown').upper()
        dev_type = finding.get('deviation_type', 'unknown').replace('_', ' ').title()
        evidence = finding.get('evidence_quote', '')[:100]
        explanation = finding.get('explanation', 'N/A')

        print(f"\n{i}. [{sev}] {dev_type}")
        print(f"   Evidence: \"{evidence}...\"")
        print(f"   Issue: {explanation}")

    # Edits
    if suggested_edits:
        print(f"\n\n✏️  SUGGESTED CHANGES\n")
        print("-" * 100)

        for i, edit in enumerate(suggested_edits, 1):
            summary = edit.get('change_summary', 'N/A')
            explanation = edit.get('explanation', 'N/A')

            print(f"\n{i}. {summary}")
            print(f"   Recommendation: {explanation[:200]}...")

    print("\n" + "=" * 100)
    print("END OF ANALYSIS")
    print("=" * 100)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quick_analyze.py <contract_file.txt>")
        print("Example: python quick_analyze.py sample_contract.txt")
        sys.exit(1)

    asyncio.run(quick_analyze(sys.argv[1]))
