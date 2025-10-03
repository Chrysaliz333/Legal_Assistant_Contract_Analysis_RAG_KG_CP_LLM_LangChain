"""
Streamlit Web UI for Contract Analysis
Drag-and-drop interface for evaluating legal output
"""

import streamlit as st
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Set API key from Streamlit secrets before importing other modules
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
elif not os.getenv("ANTHROPIC_API_KEY"):
    st.error("⚠️ ANTHROPIC_API_KEY not found. Please add it to Streamlit Cloud Secrets.")
    st.stop()

# Import analysis functions
from quick_analyze import extract_clauses_simple
from src.agents.workflow import ContractAnalysisWorkflow
from get_policies import get_policies_for_contract

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


async def analyze_contract_async(contract_text, contract_type, orientation, style_params):
    """Run async analysis"""

    # Extract clauses
    clauses = extract_clauses_simple(contract_text)

    if not clauses:
        return None, "No clauses could be extracted from the contract"

    # Load policies
    policies = get_policies_for_contract(
        contract_type=contract_type,
        model_orientation=orientation
    )

    # Run workflow
    workflow = ContractAnalysisWorkflow(enable_checkpointing=False)

    result = await workflow.analyze_contract(
        version_id=f"web-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        session_id=f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        contract_text=contract_text,
        clauses=clauses,
        policies=policies,
        style_params=style_params
    )

    return result, None


def display_results(result):
    """Display analysis results in UI"""

    findings = result.get('findings', [])
    suggested_edits = result.get('suggested_edits', [])

    # Summary statistics
    st.markdown("### 📊 Analysis Summary")

    col1, col2, col3, col4 = st.columns(4)

    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for f in findings:
        sev = f.get('severity', 'UNKNOWN').upper()
        if sev in severity_counts:
            severity_counts[sev] += 1

    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Total Issues", len(findings))
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Critical", severity_counts['CRITICAL'])
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("High Priority", severity_counts['HIGH'])
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Suggested Edits", len(suggested_edits))
        st.markdown('</div>', unsafe_allow_html=True)

    # Detailed findings
    st.markdown("---")
    st.markdown("### 🔍 Detailed Findings")

    for i, finding in enumerate(findings, 1):
        sev = finding.get('severity', 'unknown').upper()
        dev_type = finding.get('deviation_type', 'unknown').replace('_', ' ').title()
        evidence = finding.get('evidence_quote', 'N/A')[:150]
        explanation = finding.get('explanation', 'N/A')

        # Color-code severity
        sev_class = sev.lower()

        with st.expander(f"**{i}. [{sev}] {dev_type}**", expanded=(i <= 3)):
            st.markdown(f'<p class="{sev_class}">Severity: {sev}</p>', unsafe_allow_html=True)
            st.markdown(f"**Evidence:**")
            st.info(f'"{evidence}..."')
            st.markdown(f"**Issue:** {explanation}")

    # Suggested edits
    if suggested_edits:
        st.markdown("---")
        st.markdown("### ✏️ Suggested Changes")

        for i, edit in enumerate(suggested_edits, 1):
            summary = edit.get('change_summary', 'N/A')
            explanation = edit.get('explanation', 'N/A')
            edit_type = edit.get('edit_type', 'unknown')
            conflicts = len(edit.get('conflicts_with', []))

            with st.expander(f"**{i}. {summary}**", expanded=(i <= 2)):
                st.markdown(f"**Type:** `{edit_type}`")

                if conflicts > 0:
                    st.warning(f"⚠️ Conflicts with {conflicts} other edit(s)")

                st.markdown(f"**Recommendation:**")
                st.write(explanation)

                # Show deletions and insertions
                deletions = edit.get('deletions', [])
                insertions = edit.get('insertions', [])

                if deletions:
                    st.markdown("**Deletions:**")
                    for d in deletions:
                        st.markdown(f'- ~~{d.get("deleted_text", "")}~~')

                if insertions:
                    st.markdown("**Insertions:**")
                    for ins in insertions:
                        st.markdown(f'- **{ins.get("inserted_text", "")}**')


def main():
    """Main Streamlit app"""

    # Header
    st.markdown('<p class="main-header">⚖️ Legal Contract Analyzer</p>', unsafe_allow_html=True)
    st.markdown("Upload your contract to analyze it against your organization's legal policies")

    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")

        contract_type = st.selectbox(
            "Contract Type",
            ['saas', 'professional_services', 'software_license', 'cloud', 'data_processing'],
            index=0
        )

        orientation = st.selectbox(
            "Model Orientation",
            ['buy', 'sell'],
            index=0,
            help="Are you the customer (buy) or vendor (sell)?"
        )

        st.markdown("### Style Parameters")

        tone = st.selectbox("Tone", ['concise', 'balanced', 'verbose'], index=0)
        formality = st.selectbox("Formality", ['legal', 'plain_english'], index=0)
        aggressiveness = st.selectbox("Aggressiveness", ['strict', 'balanced', 'flexible'], index=0)
        audience = st.selectbox("Audience", ['internal', 'counterparty'], index=0)

        style_params = {
            'tone': tone,
            'formality': formality,
            'aggressiveness': aggressiveness,
            'audience': audience
        }

        st.markdown("---")
        st.markdown("### 📚 About")
        st.info("""
        This tool uses a 4-agent AI pipeline to:
        1. Extract contract clauses
        2. Check against policies
        3. Generate rationales
        4. Suggest edits

        **Current Database:**
        - 25 policies
        - 16 playbook rules
        """)

    # Main area - File upload
    uploaded_file = st.file_uploader(
        "📄 Drop your contract here (PDF, DOCX, or TXT)",
        type=['pdf', 'docx', 'txt'],
        help="Upload a contract file to analyze"
    )

    if uploaded_file:
        st.success(f"✅ Uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")

        # Parse button
        if st.button("🚀 Analyze Contract", type="primary"):

            # Parse file
            with st.spinner("📖 Parsing document..."):
                contract_text, error = parse_uploaded_file(uploaded_file)

            if error:
                st.error(f"❌ {error}")
                return

            # Show preview
            word_count = len(contract_text.split())
            st.info(f"📝 Extracted {word_count:,} words ({len(contract_text):,} characters)")

            with st.expander("📄 Contract Preview (first 500 chars)"):
                st.text(contract_text[:500] + "...")

            # Run analysis
            with st.spinner("🤖 Running 4-agent analysis... This may take 1-2 minutes..."):
                result, error = asyncio.run(
                    analyze_contract_async(contract_text, contract_type, orientation, style_params)
                )

            if error:
                st.error(f"❌ {error}")
                return

            # Display results
            st.success("✅ Analysis complete!")
            display_results(result)

            # Download results
            st.markdown("---")
            st.download_button(
                label="📥 Download Results (JSON)",
                data=str(result),
                file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    else:
        # Show instructions
        st.markdown("### 👋 Get Started")
        st.markdown("""
        1. **Upload a contract** using the file uploader above
        2. **Configure settings** in the sidebar (contract type, orientation, style)
        3. **Click "Analyze Contract"** to run the analysis
        4. **Review findings** and suggested edits

        ---

        **Sample Files:**
        - Try the included `sample_contract.txt` to see how it works
        - Supports PDF, DOCX, and TXT formats
        """)


if __name__ == "__main__":
    main()
