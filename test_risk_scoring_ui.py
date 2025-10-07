"""
Quick UI test script to verify risk scoring display
Run with: streamlit run test_risk_scoring_ui.py
"""

import streamlit as st
import json

# Mock analysis result with risk scores
mock_result = {
    "findings": [
        {
            "finding_id": "f1",
            "clause_reference": "Section 2 - Liability",
            "policy_violated": "LP-401",
            "severity": "critical",
            "risk_score": {
                "likelihood": 5,
                "likelihood_reasoning": "Unlimited liability clause will almost certainly be exploited in dispute scenarios",
                "impact": 5,
                "impact_reasoning": "Catastrophic financial exposure - no cap on damages, could exceed company valuation",
                "overall_score": 25,
                "risk_level": "critical"
            },
            "contract_evidence": "Company's liability is unlimited for all claims.",
            "issue_explanation": "Unlimited liability exposes the company to potentially catastrophic financial risk.",
            "suggested_edit": {
                "change_type": "value_update",
                "current_text": "Company's liability is unlimited for all claims",
                "proposed_text": "Company's liability shall be limited to fees paid in the 12 months preceding the claim",
                "rationale": "Standard industry practice limits liability to direct fees to prevent business-threatening exposure"
            }
        },
        {
            "finding_id": "f2",
            "clause_reference": "Section 1 - Payment Terms",
            "policy_violated": "FIN-203",
            "severity": "high",
            "risk_score": {
                "likelihood": 4,
                "likelihood_reasoning": "90-day payment terms are explicitly stated and likely to be enforced",
                "impact": 4,
                "impact_reasoning": "Major cash flow impact - could require external financing or impact operations",
                "overall_score": 16,
                "risk_level": "critical"
            },
            "contract_evidence": "Client shall pay all fees within 90 days of invoice date.",
            "issue_explanation": "Extended payment terms significantly impact cash flow and working capital.",
            "suggested_edit": {
                "change_type": "value_update",
                "current_text": "90 days",
                "proposed_text": "30 days",
                "rationale": "Standard net-30 payment terms align with industry practice and maintain healthy cash flow"
            }
        },
        {
            "finding_id": "f3",
            "clause_reference": "Section 3 - Termination",
            "policy_violated": "TERM-105",
            "severity": "medium",
            "risk_score": {
                "likelihood": 3,
                "likelihood_reasoning": "Termination without notice is possible but depends on business relationship",
                "impact": 3,
                "impact_reasoning": "Moderate revenue loss and operational disruption, but not business-threatening",
                "overall_score": 9,
                "risk_level": "medium"
            },
            "contract_evidence": "Either party may terminate this agreement at any time without cause or notice.",
            "issue_explanation": "Instant termination creates instability and prevents resource planning.",
            "suggested_edit": {
                "change_type": "text_replacement",
                "current_text": "at any time without cause or notice",
                "proposed_text": "with 30 days written notice",
                "rationale": "Notice period allows for orderly wind-down and minimizes disruption"
            }
        }
    ],
    "summary": {
        "total_findings": 3,
        "by_severity": {"critical": 1, "high": 1, "medium": 1, "low": 0},
        "by_risk_level": {"critical": 2, "high": 0, "medium": 1, "low": 0},
        "total_suggested_edits": 3,
        "key_themes": ["Liability exposure", "Cash flow management", "Contract stability"],
        "average_risk_score": 16.7,
        "highest_risk_finding": "f1"
    }
}

# Display using app_unified.py display logic
st.title("🎯 Risk Scoring UI Test")

st.markdown("## Mock Analysis Result with Risk Scores")

findings = mock_result.get('findings', [])
summary = mock_result.get('summary', {})
by_risk_level = summary.get('by_risk_level', {})
avg_risk = summary.get('average_risk_score', 0)

# Risk-based metrics
st.markdown("### 🎯 Risk-Based Assessment")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Findings", len(findings))

with col2:
    st.metric("Critical Risk", by_risk_level.get('critical', 0))

with col3:
    st.metric("High Risk", by_risk_level.get('high', 0))

with col4:
    st.metric("Medium Risk", by_risk_level.get('medium', 0))

with col5:
    st.metric("Avg Risk Score", f"{avg_risk:.1f}")

st.markdown("---")

# Display findings
for i, finding in enumerate(findings, 1):
    risk_score_data = finding.get('risk_score', {})
    risk_level = risk_score_data.get('risk_level', 'medium')
    overall_score = risk_score_data.get('overall_score', 0)

    risk_color = {
        'critical': '#d62728',
        'high': '#ff7f0e',
        'medium': '#ffbb78',
        'low': '#98df8a'
    }.get(risk_level, '#999999')

    with st.expander(
        f"**Finding {i}**: {finding.get('clause_reference')} - **Risk Score: {overall_score}/25** ({risk_level.upper()})",
        expanded=True
    ):
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

        st.markdown(f"**Policy Violated:** `{finding.get('policy_violated')}`")
        st.markdown(f"**Severity:** `{finding.get('severity', 'N/A').upper()}`")

        st.markdown("**Evidence:**")
        st.markdown(f"> {finding.get('contract_evidence')}")

        st.markdown("**Issue:**")
        st.write(finding.get('issue_explanation'))

st.markdown("---")
st.success("✅ Risk scoring UI successfully displays likelihood, impact, and overall risk scores!")
