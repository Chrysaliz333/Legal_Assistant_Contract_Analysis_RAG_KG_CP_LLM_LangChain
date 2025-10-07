"""
Streamlit Web UI for Contract Analysis - Unified Agent Version
Simplified single-agent approach with better results
"""

import streamlit as st
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set API key from Streamlit secrets or environment
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
elif not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ OPENAI_API_KEY not found. Please add it to Streamlit Cloud Secrets.")
    st.info("Go to: Settings → Secrets → Add `OPENAI_API_KEY = \"your-key-here\"`")
    st.stop()

# Import unified agent
from src.agents.unified_agent import UnifiedContractAgent
from get_policies import get_all_policies
from src.services.negotiation_tracker import NegotiationTracker

# Page config
st.set_page_config(
    page_title="Legal Contract Analyzer",
    page_icon="⚖️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .critical { color: #d62728; font-weight: bold; }
    .high { color: #ff7f0e; font-weight: bold; }
    .medium { color: #ffbb78; font-weight: bold; }
    .low { color: #98df8a; font-weight: bold; }
    .finding-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .edit-section {
        background-color: #f9f9f9;
        border-left: 3px solid #1f77b4;
        padding: 0.5rem 1rem;
        margin-top: 0.5rem;
    }
    .deletion {
        background-color: #ffe6e6;
        text-decoration: line-through;
        padding: 0.2rem 0.4rem;
        border-radius: 0.2rem;
    }
    .insertion {
        background-color: #e6ffe6;
        font-weight: bold;
        padding: 0.2rem 0.4rem;
        border-radius: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)


def parse_uploaded_file(uploaded_file):
    """Parse uploaded file to text"""

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # Determine file type and parse
        extension = Path(uploaded_file.name).suffix.lower()

        if extension == '.txt':
            text = Path(tmp_path).read_text(encoding='utf-8')
        elif extension == '.pdf':
            import pdfplumber
            text_parts = []
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            text = "\n\n".join(text_parts)
        elif extension in ['.docx', '.doc']:
            from docx import Document as DocxDocument
            doc = DocxDocument(tmp_path)
            text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(text_parts)
        else:
            return None, f"Unsupported file type: {extension}"

        return text, None

    except Exception as e:
        return None, f"Error parsing file: {str(e)}"

    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def analyze_contract_async(contract_text, style_params):
    """Run unified agent analysis"""

    try:
        st.info(f"📄 Contract length: {len(contract_text):,} characters")

        # Load policies
        all_policies = get_all_policies()

        # Convert to unified agent format and limit to top 15 most important
        policies = []
        for p in all_policies[:15]:  # Limit policies to prevent timeout
            policies.append({
                'policy_id': p['policy_id'],
                'title': p.get('policy_category', 'General Policy'),
                'requirement': p['policy_text']
            })

        st.info(f"📋 Loaded {len(policies)} policies for checking (limited to top 15 for performance)")

        # Create unified agent
        agent = UnifiedContractAgent(style_params=style_params)

        # Analyze
        with st.spinner("🤖 Analyzing contract with unified agent..."):
            result = await agent.analyze_contract(
                contract_text=contract_text,
                policies=policies
            )

        findings_count = len(result.get('findings', []))
        edits_count = sum(1 for f in result.get('findings', []) if f.get('suggested_edit'))

        st.success(f"✅ Analysis complete: {findings_count} findings, {edits_count} suggested edits")

        return result, None

    except Exception as e:
        return None, f"Error during analysis: {str(e)}"


def display_findings(result):
    """Display findings with suggested edits"""

    findings = result.get('findings', [])

    if not findings:
        st.info("✅ No policy violations found!")
        return

    # Summary stats
    summary = result.get('summary', {})
    by_severity = summary.get('by_severity', {})
    by_risk_level = summary.get('by_risk_level', {})
    avg_risk = summary.get('average_risk_score', 0)

    # Row 1: Risk-based metrics
    st.markdown("### 🎯 Risk-Based Assessment")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <h3>{len(findings)}</h3>
            <p>Total Findings</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        critical_risk = by_risk_level.get('critical', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="critical">{critical_risk}</h3>
            <p>Critical Risk</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        high_risk = by_risk_level.get('high', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="high">{high_risk}</h3>
            <p>High Risk</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        medium_risk = by_risk_level.get('medium', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="medium">{medium_risk}</h3>
            <p>Medium Risk</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="stat-box">
            <h3 style="color: #1f77b4;">{avg_risk:.1f}</h3>
            <p>Avg Risk Score</p>
        </div>
        """, unsafe_allow_html=True)

    # Row 2: Traditional severity + edits
    st.markdown("### 📊 Severity Distribution")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        critical_count = by_severity.get('critical', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="critical">{critical_count}</h3>
            <p>Critical Severity</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        high_count = by_severity.get('high', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="high">{high_count}</h3>
            <p>High Severity</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        medium_count = by_severity.get('medium', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="medium">{medium_count}</h3>
            <p>Medium Severity</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        low_count = by_severity.get('low', 0)
        st.markdown(f"""
        <div class="stat-box">
            <h3 class="low">{low_count}</h3>
            <p>Low Severity</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        edits_count = sum(1 for f in findings if f.get('suggested_edit'))
        st.markdown(f"""
        <div class="stat-box">
            <h3 style="color: #2ca02c;">{edits_count}</h3>
            <p>Suggested Edits</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Display each finding
    for i, finding in enumerate(findings, 1):
        severity = finding.get('severity', 'medium')
        risk_score_data = finding.get('risk_score', {})
        risk_level = risk_score_data.get('risk_level', 'medium')
        overall_score = risk_score_data.get('overall_score', 0)

        severity_color = {
            'critical': '#d62728',
            'high': '#ff7f0e',
            'medium': '#ffbb78',
            'low': '#98df8a'
        }.get(severity, '#999999')

        risk_color = {
            'critical': '#d62728',
            'high': '#ff7f0e',
            'medium': '#ffbb78',
            'low': '#98df8a'
        }.get(risk_level, '#999999')

        with st.expander(
            f"**Finding {i}**: {finding.get('clause_reference', 'Unknown Clause')} - "
            f"**Risk Score: {overall_score}/25** ({risk_level.upper()})",
            expanded=(i <= 3)
        ):
            # Risk Score Visualization
            if risk_score_data:
                st.markdown("### ⚠️ Risk Assessment")

                col_risk1, col_risk2, col_risk3 = st.columns(3)

                with col_risk1:
                    likelihood = risk_score_data.get('likelihood', 0)
                    st.markdown(f"""
                    <div style="text-align: center; padding: 0.5rem; background-color: {risk_color}20; border-radius: 0.5rem;">
                        <h4 style="margin: 0;">Likelihood: {likelihood}/5</h4>
                        <p style="margin: 0; font-size: 0.8rem;">{risk_score_data.get('likelihood_reasoning', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col_risk2:
                    impact = risk_score_data.get('impact', 0)
                    st.markdown(f"""
                    <div style="text-align: center; padding: 0.5rem; background-color: {risk_color}20; border-radius: 0.5rem;">
                        <h4 style="margin: 0;">Impact: {impact}/5</h4>
                        <p style="margin: 0; font-size: 0.8rem;">{risk_score_data.get('impact_reasoning', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col_risk3:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 0.5rem; background-color: {risk_color}; color: white; border-radius: 0.5rem;">
                        <h4 style="margin: 0;">Overall: {overall_score}/25</h4>
                        <p style="margin: 0; font-size: 0.8rem; font-weight: bold;">{risk_level.upper()} RISK</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")

            # Policy violated
            st.markdown(f"**Policy Violated:** `{finding.get('policy_violated', 'Unknown')}`")
            st.markdown(f"**Severity Classification:** `{severity.upper()}`")

            # Contract evidence
            st.markdown("**Evidence from Contract:**")
            st.markdown(f"> {finding.get('contract_evidence', 'No evidence provided')}")

            # Explanation
            st.markdown("**Issue Explanation:**")
            st.write(finding.get('issue_explanation', 'No explanation provided'))

            # Suggested edit
            suggested_edit = finding.get('suggested_edit')
            if suggested_edit:
                st.markdown("### 📝 Suggested Edit")

                change_summary = suggested_edit.get('change_summary', 'No summary')
                st.info(f"**Change:** {change_summary}")

                # Show track changes
                current_text = suggested_edit.get('current_text', '')
                proposed_text = suggested_edit.get('proposed_text', '')

                col_a, col_b = st.columns(2)

                with col_a:
                    st.markdown("**Current Text:**")
                    st.markdown(f'<div class="deletion">{current_text[:200]}...</div>', unsafe_allow_html=True)

                with col_b:
                    st.markdown("**Proposed Text:**")
                    st.markdown(f'<div class="insertion">{proposed_text[:200]}...</div>', unsafe_allow_html=True)

                # Rationale
                rationale = suggested_edit.get('rationale', 'No rationale provided')
                st.markdown(f"**Rationale:** {rationale}")

                # Fallback options
                fallback_options = finding.get('fallback_options', [])
                if fallback_options:
                    st.markdown("**Alternative Options:**")
                    for j, option in enumerate(fallback_options, 1):
                        st.markdown(f"{j}. {option.get('alternative_text', 'No text')}")
                        if option.get('conditions'):
                            st.markdown(f"   - Conditions: {', '.join(option['conditions'])}")
                        st.markdown(f"   - Risk Level: {option.get('risk_level', 'unknown').upper()}")


def main():
    """Main Streamlit app"""

    # Initialize negotiation tracker
    if 'negotiation_tracker' not in st.session_state:
        st.session_state.negotiation_tracker = NegotiationTracker()

    if 'current_negotiation_id' not in st.session_state:
        st.session_state.current_negotiation_id = None

    # Header
    st.markdown('<h1 class="main-header">⚖️ Legal Contract Analyzer</h1>', unsafe_allow_html=True)
    st.markdown("**Unified Agent** - Context-aware contract analysis with negotiation tracking")

    # Sidebar - Negotiation Management
    st.sidebar.header("📁 Negotiation")

    tracker = st.session_state.negotiation_tracker

    # List existing negotiations
    negotiations = tracker.list_negotiations()

    if negotiations:
        negotiation_options = {f"{n['title']} ({n['version_count']} versions)": n['negotiation_id'] for n in negotiations}
        negotiation_options["+ Start New Negotiation"] = None

        selected_label = st.sidebar.selectbox(
            "Select Negotiation",
            options=list(negotiation_options.keys()),
            index=0
        )

        selected_neg_id = negotiation_options[selected_label]

        if selected_neg_id:
            st.session_state.current_negotiation_id = selected_neg_id
        else:
            # Create new negotiation
            new_title = st.sidebar.text_input("New Negotiation Title", value="New Contract Negotiation")
            if st.sidebar.button("Create"):
                import uuid
                new_id = f"neg_{uuid.uuid4().hex[:8]}"
                tracker.create_negotiation(new_id, new_title)
                st.session_state.current_negotiation_id = new_id
                st.rerun()
    else:
        # No negotiations yet - auto-create first one
        st.sidebar.info("No negotiations yet. Upload a contract to start.")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Analysis Settings")

    st.sidebar.markdown("### Party Representation")

    party = st.sidebar.selectbox(
        "You are representing:",
        ["buyer", "seller"],
        index=0,
        help="Are you representing the buyer (customer) or seller (vendor)?"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Communication Style")

    tone = st.sidebar.selectbox(
        "Tone",
        ["concise", "balanced", "verbose"],
        index=1,
        help="Controls explanation length"
    )

    formality = st.sidebar.selectbox(
        "Formality",
        ["legal", "plain_english"],
        index=0,
        help="Legal terminology vs plain language"
    )

    aggressiveness = st.sidebar.selectbox(
        "Aggressiveness",
        ["strict", "balanced", "flexible"],
        index=1,
        help="Mandatory language vs recommendations"
    )

    audience = st.sidebar.selectbox(
        "Audience",
        ["internal", "counterparty"],
        index=0,
        help="Internal legal team vs external parties"
    )

    style_params = {
        'party': party,
        'tone': tone,
        'formality': formality,
        'aggressiveness': aggressiveness,
        'audience': audience
    }

    # Display current style
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Current Configuration:**")
    st.sidebar.json(style_params)

    # File upload
    st.header("📤 Upload Contract")

    # Create or get negotiation
    if not st.session_state.current_negotiation_id:
        # Auto-create first negotiation
        import uuid
        new_id = f"neg_{uuid.uuid4().hex[:8]}"
        tracker.create_negotiation(new_id, uploaded_file.name if 'uploaded_file' in locals() else "New Negotiation")
        st.session_state.current_negotiation_id = new_id

    uploaded_file = st.file_uploader(
        "Drop your contract here (.txt, .pdf, .docx)",
        type=['txt', 'pdf', 'docx', 'doc']
    )

    if uploaded_file:
        # Parse file
        contract_text, error = parse_uploaded_file(uploaded_file)

        if error:
            st.error(error)
            return

        if not contract_text or not contract_text.strip():
            st.error("❌ Contract file is empty or could not be parsed.")
            return

        # Show contract preview
        with st.expander("📄 Contract Preview", expanded=False):
            st.text(contract_text[:2000] + ("..." if len(contract_text) > 2000 else ""))

        # Version metadata
        col1, col2 = st.columns(2)

        with col1:
            uploaded_by = st.radio(
                "This version is from:",
                ['internal', 'counterparty'],
                horizontal=True
            )

        with col2:
            version_notes = st.text_input(
                "Notes (optional)",
                placeholder="e.g., Counterparty increased liability cap"
            )

        # Analyze button
        if st.button("🚀 Analyze Contract", type="primary"):
            # Run analysis
            result, error = asyncio.run(analyze_contract_async(contract_text, style_params))

            if error:
                st.error(error)
                return

            # Save version to negotiation tracker
            try:
                version = tracker.add_version(
                    st.session_state.current_negotiation_id,
                    contract_text,
                    uploaded_by=uploaded_by,
                    notes=version_notes if version_notes else None,
                    analysis_result=result
                )
                st.success(f"✅ Saved as {version.version_id}")
            except ValueError as e:
                st.warning(f"⚠️ {str(e)}")

            # Display results
            st.header("📊 Analysis Results")
            display_findings(result)

            # Download results
            st.markdown("---")
            st.subheader("💾 Export Results")

            col1, col2 = st.columns(2)

            with col1:
                json_str = json.dumps(result, indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            with col2:
                # Create summary report
                findings = result.get('findings', [])
                summary = result.get('summary', {})

                report = f"""# Contract Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total Findings: {summary.get('total_findings', 0)}
- Critical: {summary.get('by_severity', {}).get('critical', 0)}
- High: {summary.get('by_severity', {}).get('high', 0)}
- Medium: {summary.get('by_severity', {}).get('medium', 0)}
- Low: {summary.get('by_severity', {}).get('low', 0)}
- Suggested Edits: {summary.get('total_suggested_edits', 0)}

## Findings

"""
                for i, finding in enumerate(findings, 1):
                    report += f"""### {i}. {finding.get('clause_reference', 'Unknown')} - {finding.get('severity', 'medium').upper()}

**Policy:** {finding.get('policy_violated', 'Unknown')}

**Evidence:**
> {finding.get('contract_evidence', 'No evidence')}

**Issue:**
{finding.get('issue_explanation', 'No explanation')}

"""
                    if finding.get('suggested_edit'):
                        edit = finding['suggested_edit']
                        report += f"""**Suggested Edit:**
- Change: {edit.get('change_summary', 'No summary')}
- Current: {edit.get('current_text', 'N/A')[:100]}...
- Proposed: {edit.get('proposed_text', 'N/A')[:100]}...
- Rationale: {edit.get('rationale', 'No rationale')}

"""
                    report += "---\n\n"

                st.download_button(
                    label="📥 Download Report (Markdown)",
                    data=report,
                    file_name=f"contract_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

            # Show negotiation timeline
            st.markdown("---")
            st.header("📋 Negotiation Timeline")

            timeline = tracker.get_negotiation_timeline(st.session_state.current_negotiation_id)

            if len(timeline) > 1:
                st.info(f"📊 {len(timeline)} versions in this negotiation")

            for entry in timeline:
                with st.expander(
                    f"**Version {entry['version_number']}** - {entry['uploaded_by'].title()} ({entry['uploaded_at'][:10]})",
                    expanded=(entry['version_number'] == len(timeline))
                ):
                    st.markdown(f"**Uploaded:** {entry['uploaded_at']}")
                    st.markdown(f"**Source:** {entry['uploaded_by'].title()}")

                    if entry.get('notes'):
                        st.markdown(f"**Notes:** {entry['notes']}")

                    if entry.get('analysis_summary'):
                        summary = entry['analysis_summary']
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Findings", summary['total_findings'])
                        with col2:
                            st.metric("Critical", summary['critical'])
                        with col3:
                            st.metric("High", summary['high'])
                        with col4:
                            st.metric("Edits", summary['suggested_edits'])

            # Version comparison
            if len(timeline) > 1:
                st.markdown("---")
                st.header("🔀 Compare Versions")

                col1, col2 = st.columns(2)

                with col1:
                    v1_num = st.selectbox(
                        "Base Version",
                        [i + 1 for i in range(len(timeline))],
                        index=len(timeline) - 2
                    )

                with col2:
                    v2_num = st.selectbox(
                        "Compare To",
                        [i + 1 for i in range(len(timeline))],
                        index=len(timeline) - 1
                    )

                if st.button("Compare Selected Versions"):
                    v1_id = timeline[v1_num - 1]['version_id']
                    v2_id = timeline[v2_num - 1]['version_id']

                    comparison = tracker.compare_versions(v1_id, v2_id)

                    st.markdown(f"### Changes: Version {v1_num} → Version {v2_num}")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Additions", comparison['summary']['additions'])
                    with col_b:
                        st.metric("Deletions", comparison['summary']['deletions'])
                    with col_c:
                        st.metric("Total Changes", comparison['summary']['total_changes'])

                    st.markdown("### Unified Diff")
                    st.code(comparison['diff_unified'], language='diff')

    # Show timeline and comparison for existing negotiations (outside analyze button)
    if st.session_state.current_negotiation_id:
        timeline = tracker.get_negotiation_timeline(st.session_state.current_negotiation_id)

        if len(timeline) > 0:
            st.markdown("---")
            st.header("📋 Negotiation History")
            st.info(f"📊 {len(timeline)} version(s) in this negotiation")

            # Timeline
            for entry in timeline:
                with st.expander(
                    f"**Version {entry['version_number']}** - {entry['uploaded_by'].title()} ({entry['uploaded_at'][:10]})",
                    expanded=False
                ):
                    st.markdown(f"**Uploaded:** {entry['uploaded_at']}")
                    st.markdown(f"**Source:** {entry['uploaded_by'].title()}")

                    if entry.get('notes'):
                        st.markdown(f"**Notes:** {entry['notes']}")

                    if entry.get('analysis_summary'):
                        summary = entry['analysis_summary']
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Findings", summary['total_findings'])
                        with col2:
                            st.metric("Critical", summary['critical'])
                        with col3:
                            st.metric("High", summary['high'])
                        with col4:
                            st.metric("Edits", summary['suggested_edits'])

            # Comparison (only if 2+ versions)
            if len(timeline) > 1:
                st.markdown("---")
                st.header("🔀 Compare Versions")

                col1, col2 = st.columns(2)

                with col1:
                    v1_num = st.selectbox(
                        "Base Version",
                        [i + 1 for i in range(len(timeline))],
                        index=max(0, len(timeline) - 2),
                        key="compare_v1"
                    )

                with col2:
                    v2_num = st.selectbox(
                        "Compare To",
                        [i + 1 for i in range(len(timeline))],
                        index=len(timeline) - 1,
                        key="compare_v2"
                    )

                if st.button("🔍 Compare Selected Versions"):
                    v1_id = timeline[v1_num - 1]['version_id']
                    v2_id = timeline[v2_num - 1]['version_id']

                    comparison = tracker.compare_versions(v1_id, v2_id)

                    st.markdown(f"### Changes: Version {v1_num} → Version {v2_num}")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Additions", comparison['summary']['additions'])
                    with col_b:
                        st.metric("Deletions", comparison['summary']['deletions'])
                    with col_c:
                        st.metric("Total Changes", comparison['summary']['total_changes'])

                    st.markdown("### Unified Diff")
                    st.code(comparison['diff_unified'], language='diff')


if __name__ == "__main__":
    main()
