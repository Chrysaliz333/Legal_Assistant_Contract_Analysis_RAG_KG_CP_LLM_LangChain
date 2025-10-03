"""
File Upload Demo - Analyze Real Contract Documents
Supports PDF and DOCX files with LLM-based clause extraction
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import json

# Document parsing libraries
import pdfplumber
from docx import Document as DocxDocument

# LangChain for LLM-based extraction
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Import existing workflow and policy loader
from src.agents.workflow import ContractAnalysisWorkflow
from get_policies import get_policies_for_contract
from config.settings import settings


# =============================================================================
# DOCUMENT PARSERS
# =============================================================================

def parse_pdf(file_path: str) -> str:
    """
    Extract text from PDF file

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text content
    """
    text_parts = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

    full_text = "\n\n".join(text_parts)
    return full_text


def parse_docx(file_path: str) -> str:
    """
    Extract text from DOCX file

    Args:
        file_path: Path to DOCX file

    Returns:
        Extracted text content
    """
    doc = DocxDocument(file_path)

    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    full_text = "\n\n".join(text_parts)
    return full_text


def parse_document(file_path: str) -> str:
    """
    Auto-detect file type and parse

    Args:
        file_path: Path to document file

    Returns:
        Extracted text content

    Raises:
        ValueError: If file type not supported
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    if extension == '.pdf':
        return parse_pdf(str(file_path))
    elif extension in ['.docx', '.doc']:
        return parse_docx(str(file_path))
    elif extension == '.txt':
        return file_path.read_text(encoding='utf-8')
    else:
        raise ValueError(f"Unsupported file type: {extension}. Supported: .pdf, .docx, .txt")


# =============================================================================
# LLM-BASED CLAUSE EXTRACTION
# =============================================================================

async def extract_clauses_with_llm(contract_text: str, contract_type: str = 'saas') -> List[Dict]:
    """
    Use Claude to intelligently extract and classify contract clauses

    Args:
        contract_text: Full contract text
        contract_type: Type of contract (saas, professional_services, etc.)

    Returns:
        List of extracted clauses with classification
    """
    # Use Haiku for fast extraction
    llm = ChatAnthropic(
        model="claude-3-5-haiku-20241022",
        max_tokens=4096,
        temperature=0.1,
        timeout=60,  # 60 second timeout for extraction
        anthropic_api_key=settings.ANTHROPIC_API_KEY
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a legal document parser specialized in contract analysis.

Your task: Extract all distinct clauses from the contract and classify them.

Common clause types:
- service_levels (SLA, uptime, availability)
- limitation_of_liability (liability caps, exclusions)
- data_protection (GDPR, DPA, privacy)
- governing_law (jurisdiction, dispute resolution)
- indemnity (IP infringement, third-party claims)
- payment_terms (invoicing, payment deadlines)
- termination (termination rights, notice periods)
- confidentiality (NDA, confidential information)
- intellectual_property (IP ownership, licenses)
- warranty (warranties, representations)
- insurance (coverage requirements)
- audit_rights (audit, inspection rights)
- automatic_renewal (auto-renewal, notice)
- assignment (assignment restrictions)
- force_majeure (force majeure events)

Return ONLY a JSON array (no markdown, no code blocks):
[
  {{
    "clause_identifier": "Section 1.2" or "Article 5" or "Clause 3(a)",
    "clause_type": "one of the types above",
    "clause_text": "full verbatim text of the clause (200-500 words max per clause)",
    "confidence": 0.0-1.0
  }}
]

Rules:
1. Extract complete clauses (not partial sentences)
2. Each clause should be self-contained
3. Preserve original text exactly
4. Classify using the types listed above
5. If uncertain about type, use "other" and note in clause_type_note field
6. Include section numbers/identifiers if present"""),
        ("user", """Contract Type: {contract_type}

Contract Text:
{contract_text}

Extract all clauses and return JSON array:""")
    ])

    try:
        # Truncate very long contracts (Claude has token limits)
        max_chars = 50000  # ~12k tokens
        if len(contract_text) > max_chars:
            print(f"⚠️  Contract is large ({len(contract_text)} chars), truncating to {max_chars} chars for extraction")
            contract_text = contract_text[:max_chars] + "\n\n[... document truncated ...]"

        # Invoke Claude
        response = await llm.ainvoke(
            prompt.format(
                contract_type=contract_type,
                contract_text=contract_text
            )
        )

        # Parse response
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith('```'):
            content = content.split('\n', 1)[1]  # Remove first line
            content = content.rsplit('\n```', 1)[0]  # Remove last line

        clauses_raw = json.loads(content)

        # Add unique IDs and normalize
        clauses = []
        for i, clause in enumerate(clauses_raw, 1):
            clauses.append({
                'clause_id': f"clause-{i}",
                'clause_identifier': clause.get('clause_identifier', f'Clause {i}'),
                'clause_type': clause.get('clause_type', 'other'),
                'clause_text': clause.get('clause_text', ''),
                'extraction_confidence': clause.get('confidence', 0.8)
            })

        print(f"✅ Extracted {len(clauses)} clauses using LLM")
        return clauses

    except json.JSONDecodeError as e:
        print(f"❌ Error parsing LLM response: {e}")
        print(f"Response was: {content[:200]}...")
        return []

    except Exception as e:
        print(f"❌ Error extracting clauses: {e}")
        return []


# =============================================================================
# MAIN ANALYSIS WORKFLOW
# =============================================================================

async def analyze_contract_file(
    file_path: str,
    contract_type: str = 'saas',
    model_orientation: str = 'buy',
    style_params: Optional[Dict] = None
) -> Dict:
    """
    Complete workflow: File → Parse → Extract → Analyze

    Args:
        file_path: Path to contract file (PDF, DOCX, TXT)
        contract_type: Type of contract (saas, professional_services, etc.)
        model_orientation: buy (we're customer) or sell (we're vendor)
        style_params: Style configuration for output

    Returns:
        Complete analysis results
    """
    print("=" * 100)
    print("CONTRACT FILE ANALYSIS")
    print("=" * 100)
    print(f"📄 File: {file_path}")
    print(f"📋 Contract Type: {contract_type}")
    print(f"🔄 Orientation: {model_orientation}")
    print()

    # Step 1: Parse document
    print("🔍 STEP 1: Parsing Document")
    print("-" * 100)

    try:
        contract_text = parse_document(file_path)
        word_count = len(contract_text.split())
        char_count = len(contract_text)

        print(f"✅ Extracted {word_count:,} words ({char_count:,} characters)")
        print(f"📝 Preview: {contract_text[:200]}...")
        print()

    except Exception as e:
        print(f"❌ Error parsing document: {e}")
        return {'error': str(e), 'stage': 'parsing'}

    # Step 2: Extract clauses with LLM
    print("🤖 STEP 2: Extracting Clauses with LLM")
    print("-" * 100)

    clauses = await extract_clauses_with_llm(contract_text, contract_type)

    if not clauses:
        print("❌ No clauses extracted. Cannot continue.")
        return {'error': 'No clauses extracted', 'stage': 'extraction'}

    print(f"\nExtracted {len(clauses)} clauses:")
    for clause in clauses[:5]:  # Show first 5
        print(f"  - {clause['clause_identifier']:20s} [{clause['clause_type']:25s}] {clause['clause_text'][:60]}...")

    if len(clauses) > 5:
        print(f"  ... and {len(clauses) - 5} more")
    print()

    # Step 3: Load policies
    print("📚 STEP 3: Loading Policies from Database")
    print("-" * 100)

    policies = get_policies_for_contract(
        contract_type=contract_type,
        model_orientation=model_orientation
    )

    print(f"✅ Loaded {len(policies)} applicable policies")
    print()

    # Step 4: Run 4-agent analysis
    print("🚀 STEP 4: Running 4-Agent Analysis Pipeline")
    print("-" * 100)
    print("This may take 60-120 seconds depending on contract complexity...\n")

    # Default style params
    if style_params is None:
        style_params = {
            'tone': 'concise',
            'formality': 'legal',
            'aggressiveness': 'strict',
            'audience': 'internal'
        }

    print(f"Style Configuration:")
    for key, value in style_params.items():
        print(f"  - {key}: {value}")
    print()

    start_time = datetime.now()

    # Run workflow
    workflow = ContractAnalysisWorkflow(enable_checkpointing=False)

    result = await workflow.analyze_contract(
        version_id=f"file-{Path(file_path).stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        session_id=f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        contract_text=contract_text,
        clauses=clauses,
        policies=policies,
        style_params=style_params
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"✅ Analysis complete in {elapsed:.1f} seconds\n")

    # Step 5: Display results
    print_analysis_results(result)

    return result


def print_analysis_results(result: Dict):
    """Print formatted analysis results"""

    print("=" * 100)
    print("ANALYSIS RESULTS")
    print("=" * 100)

    findings = result.get('findings', [])
    neutral_rationales = result.get('neutral_rationales', [])
    transformed_rationales = result.get('transformed_rationales', [])
    suggested_edits = result.get('suggested_edits', [])

    # Summary stats
    print(f"\n📊 Summary Statistics:")
    print(f"  - Total Findings: {len(findings)}")

    severity_counts = {}
    for finding in findings:
        sev = finding.get('severity', 'unknown').upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if sev in severity_counts:
            print(f"  - {sev} Issues: {severity_counts[sev]}")

    print(f"  - Suggested Edits: {len(suggested_edits)}")

    conflicts = sum(1 for edit in suggested_edits if edit.get('conflicts_with'))
    print(f"  - Edits with Conflicts: {conflicts}")

    # Detailed findings
    print(f"\n🔍 DETAILED FINDINGS:")
    print("-" * 100)

    for i, finding in enumerate(findings, 1):
        severity = finding.get('severity', 'unknown').upper()
        deviation = finding.get('deviation_type', 'unknown')
        evidence = finding.get('evidence_quote', 'N/A')[:80]
        explanation = finding.get('explanation', 'N/A')

        print(f"\n{i}. [{severity}] {deviation.replace('_', ' ').title()}")
        print(f"   Evidence: \"{evidence}...\"")
        print(f"   Explanation: {explanation}")

    # Suggested edits
    if suggested_edits:
        print(f"\n✏️  SUGGESTED EDITS (Track Changes):")
        print("-" * 100)

        for i, edit in enumerate(suggested_edits, 1):
            edit_type = edit.get('edit_type', 'unknown')
            summary = edit.get('change_summary', 'N/A')
            status = edit.get('status', 'pending').upper()
            conflicts = len(edit.get('conflicts_with', []))

            print(f"\n{i}. {summary}")
            print(f"   Type: {edit_type} | Status: {status}")
            if conflicts > 0:
                print(f"   ⚠️  CONFLICTS with {conflicts} other edit(s)")

    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)


# =============================================================================
# CLI INTERFACE
# =============================================================================

async def main():
    """Command-line interface"""

    if len(sys.argv) < 2:
        print("Usage: python analyze_file.py <contract_file.pdf|docx|txt> [contract_type] [orientation]")
        print()
        print("Examples:")
        print("  python analyze_file.py my_contract.pdf")
        print("  python analyze_file.py vendor_agreement.docx saas buy")
        print("  python analyze_file.py service_agreement.pdf professional_services buy")
        print()
        print("Contract types: saas, professional_services, software_license, cloud, data_processing")
        print("Orientation: buy (we're customer) | sell (we're vendor)")
        sys.exit(1)

    file_path = sys.argv[1]
    contract_type = sys.argv[2] if len(sys.argv) > 2 else 'saas'
    orientation = sys.argv[3] if len(sys.argv) > 3 else 'buy'

    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        print("Please set it in your .env file or export it:")
        print("  export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    print(f"✅ ANTHROPIC_API_KEY found\n")

    # Run analysis
    await analyze_contract_file(
        file_path=file_path,
        contract_type=contract_type,
        model_orientation=orientation
    )


if __name__ == "__main__":
    asyncio.run(main())
