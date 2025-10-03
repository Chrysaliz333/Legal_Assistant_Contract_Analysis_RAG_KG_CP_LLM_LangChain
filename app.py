"""
Streamlit Web UI for Contract Analysis
Drag-and-drop interface for evaluating legal output
"""

import streamlit as st
import asyncio
from pathlib import Path
from datetime import datetime
from collections import defaultdict
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
from get_policies import get_policies_for_contract
from src.orchestration import AdaptiveOrchestrator

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

# Initialize session-level orchestration state for negotiation tracking
if "project_id" not in st.session_state:
    st.session_state["project_id"] = f"project-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
if "session_id" not in st.session_state:
    st.session_state["session_id"] = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
if "orchestrator" not in st.session_state:
    st.session_state["orchestrator"] = AdaptiveOrchestrator()


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


async def analyze_contract_async(contract_text, contract_type, orientation, style_params, project_id, session_id, orchestrator):
    """Run async analysis"""

    try:
        # Extract clauses
        clauses = extract_clauses_simple(contract_text)

        if not clauses:
            return None, "❌ No clauses could be extracted from the contract. Please check that your document has clear section headers (e.g., '1.', 'Section 1:', 'PAYMENT TERMS')."

        # Debug: Log clause extraction with type breakdown
        clause_types = {}
        for c in clauses:
            ctype = c.get('clause_type', 'unknown')
            clause_types[ctype] = clause_types.get(ctype, 0) + 1

        clause_type_summary = ", ".join([f"{k}: {v}" for k, v in sorted(clause_types.items())])
        st.info(f"✅ Extracted {len(clauses)} clauses from contract")
        st.info(f"📋 Clause types: {clause_type_summary}")

        # Load policies
        policies = get_policies_for_contract(
            contract_type=contract_type,
            model_orientation=orientation
        )

        if not policies:
            return None, "❌ No policies found for this contract type and orientation."

        # Debug: Log policy loading
        st.info(f"✅ Loaded {len(policies)} policies for checking")

        version_id = f"{session_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        preference_payload = {
            f"style.{key}": value for key, value in (style_params or {}).items()
        }

        context_id = orchestrator.ingest_contract(
            project_id=project_id,
            session_id=session_id,
            version_id=version_id,
            contract_text=contract_text,
            clauses=clauses,
            policies=policies,
            preferences=preference_payload if preference_payload else None,
            style_params=style_params,
        )

        await orchestrator.run(max_iterations=50)
        result = orchestrator.build_result(context_id)

        if not result:
            return None, "❌ Unable to retrieve analysis results from orchestrator."

        # Debug: Log result summary
        findings_count = len(result.get('findings', []))
        errors_count = len(result.get('errors', []))
        st.info(f"✅ Analysis complete: {findings_count} findings, {errors_count} errors")

        # Show errors if any
        if errors_count > 0:
            st.warning(f"⚠️ {errors_count} errors occurred during analysis:")
            for error in result.get('errors', []):
                st.error(error)

        return result, None

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return None, f"❌ Analysis error: {str(e)}\n\nDetails:\n{error_details}"


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


def display_negotiation_history(orchestrator, project_id: str) -> None:
    """Render contract version timeline with diff snippets and agent events."""

    st.markdown("---")
    st.markdown("### 🗂️ Negotiation History")

    history = orchestrator.memory.get_version_history(project_id)
    if not history:
        st.info("Upload additional revisions to build the negotiation timeline.")
        return

    events_by_version = defaultdict(list)
    for event in orchestrator.memory.get_agent_events(project_id):
        events_by_version[event.get('version_id', '')].append(event)

    with st.expander("View timeline", expanded=True):
        for idx, record in enumerate(reversed(history), start=1):
            created_at = record.get('created_at')
            try:
                created_display = (
                    datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M UTC')
                    if created_at
                    else 'unknown'
                )
            except ValueError:
                created_display = created_at or 'unknown'

            st.markdown(f"#### Version {record.get('version_id', 'unknown')}")
            st.caption(
                f"Source: `{record.get('source', 'unknown')}` • Recorded {created_display}"
            )

            if record.get('notes'):
                st.write(record['notes'])

            diff_snippet = record.get('diff_summary')
            if diff_snippet:
                st.code(diff_snippet, language='diff')
            else:
                st.caption("No diff available (initial upload or unchanged).")

            events = events_by_version.get(record.get('version_id', ''), [])
            if events:
                st.caption("Agent activity")
                for event in events:
                    task_type = event.get('payload', {}).get('task_type')
                    descriptor = f" – {task_type}" if task_type else ''
                    st.write(
                        f"• {event.get('timestamp', '')}: {event.get('agent')}"
                        f" {event.get('action')}{descriptor}"
                    )

            if idx < len(history):
                st.markdown('---')

def main():
    """Main Streamlit app"""

    # Header
    st.markdown('<p class="main-header">⚖️ Legal Contract Analyzer</p>', unsafe_allow_html=True)
    st.markdown("Upload your contract to analyze it against your organization's legal policies")

    # Sidebar - Configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")

        orchestrator = st.session_state["orchestrator"]
        project_id = st.session_state["project_id"]
        session_id = st.session_state["session_id"]
        saved_prefs = orchestrator.memory.get_preferences(project_id, session_id)

        def pref_value(key: str, fallback: str) -> str:
            entry = saved_prefs.get(key)
            if entry:
                val = entry.get('value')
                if isinstance(val, str) and val:
                    return val
            return fallback

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

        tone_options = ['concise', 'balanced', 'verbose']
        tone_pref = pref_value('style.tone', tone_options[0])
        tone_index = tone_options.index(tone_pref) if tone_pref in tone_options else 0
        tone = st.selectbox("Tone", tone_options, index=tone_index)

        formality_options = ['legal', 'plain_english']
        formality_pref = pref_value('style.formality', formality_options[0])
        formality_index = formality_options.index(formality_pref) if formality_pref in formality_options else 0
        formality = st.selectbox("Formality", formality_options, index=formality_index)

        aggressiveness_options = ['strict', 'balanced', 'flexible']
        aggressiveness_pref = pref_value('style.aggressiveness', aggressiveness_options[1])
        if aggressiveness_pref not in aggressiveness_options:
            aggressiveness_pref = aggressiveness_options[1]
        aggressiveness_index = aggressiveness_options.index(aggressiveness_pref)
        aggressiveness = st.selectbox("Aggressiveness", aggressiveness_options, index=aggressiveness_index)

        audience_options = ['internal', 'counterparty']
        audience_pref = pref_value('style.audience', audience_options[0])
        audience_index = audience_options.index(audience_pref) if audience_pref in audience_options else 0
        audience = st.selectbox("Audience", audience_options, index=audience_index)

        style_params = {
            'tone': tone,
            'formality': formality,
            'aggressiveness': aggressiveness,
            'audience': audience
        }

        st.markdown("### 🧭 Saved Preferences")
        if saved_prefs:
            for key, payload in sorted(saved_prefs.items()):
                value = payload.get('value')
                updated = payload.get('updated_at', '')
                try:
                    updated_display = (
                        datetime.fromisoformat(updated).strftime('%Y-%m-%d %H:%M UTC')
                        if updated
                        else 'unknown'
                    )
                except ValueError:
                    updated_display = updated or 'unknown'
                st.caption(f"`{key}` → {value} (updated {updated_display})")
        else:
            st.caption("No saved preferences yet. Add one below.")

        with st.form("preference_form", clear_on_submit=True):
            pref_key = st.text_input("Preference Key", placeholder="e.g., style.tone")
            pref_value = st.text_input("Preference Value", placeholder="e.g., concise")
            pref_reason = st.text_area("Rationale (optional)", height=60)
            submitted = st.form_submit_button("Save Preference")

        if submitted:
            if pref_key and pref_value:
                orchestrator.memory.record_preference(
                    project_id=project_id,
                    user_id=session_id,
                    key=pref_key,
                    value=pref_value,
                    rationale=pref_reason or None,
                    source="ui",
                )
                st.success(f"Preference `{pref_key}` saved.")
                st.experimental_rerun()
            else:
                st.warning("Please provide both a key and value before saving.")

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
            with st.spinner("🤖 Running adaptive multi-agent analysis..."):
                result, error = asyncio.run(
                    analyze_contract_async(
                        contract_text,
                        contract_type,
                        orientation,
                        style_params,
                        project_id,
                        session_id,
                        orchestrator,
                    )
                )

            if error:
                st.error(f"❌ {error}")
                return

            # Display results
            st.success("✅ Analysis complete!")
            display_results(result)
            display_negotiation_history(st.session_state["orchestrator"], st.session_state["project_id"])

            # Download results
            st.markdown("---")
            st.download_button(
                label="📥 Download Results (JSON)",
                data=str(result),
                file_name=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    else:
        # Show existing timeline (if any) even without active upload
        display_negotiation_history(orchestrator, project_id)

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
