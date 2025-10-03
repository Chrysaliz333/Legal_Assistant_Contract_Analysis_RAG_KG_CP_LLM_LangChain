"""
Neutral Rationale Agent
REQ-NR-001: Neutral Rationale Generation (evidence-grounded)
REQ-NR-002: Proposed Changes (specific, actionable)
REQ-NR-003: Fallback Options (when policy allows)
REQ-NR-004: Strict Separation (no tone/aggressiveness)
REQ-NR-005: Schema Validation
"""

from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime
import json
import re

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from textblob import TextBlob

from config.settings import settings
from src.agents.state import AnalysisContext, update_context_metadata, log_error_to_context


class NeutralRationaleAgent:
    """
    Neutral Rationale Agent - Second stage of analysis

    Responsibilities:
    - Generate objective, neutral explanations for each finding
    - Propose specific, actionable changes
    - Identify fallback options when policy permits
    - Maintain strict neutrality (no tone/aggressiveness)
    - Validate all output against schema
    """

    # Prohibited words that imply tone/aggressiveness (REQ-NR-004)
    PROHIBITED_WORDS = [
        'must', 'should', 'required', 'mandatory', 'essential',
        'consider', 'perhaps', 'might', 'recommend', 'suggest',
        'dangerous', 'unacceptable', 'critical', 'urgent', 'imperative'
    ]

    def __init__(self):
        # Use Sonnet 3.5 for balanced speed/quality in rationale generation
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Balanced model for objective analysis
            max_tokens=1024,  # Rationale + proposed change
            temperature=0.2,  # Low temperature for neutral, objective output
            timeout=30,
            openai_api_key=settings.OPENAI_API_KEY
        )

    async def process(self, state: AnalysisContext) -> AnalysisContext:
        """
        Main entry point for agent processing

        Args:
            state: Current analysis context with findings

        Returns:
            Updated context with neutral_rationales added
        """
        # Update metadata
        state = update_context_metadata(state, "NeutralRationaleAgent", "rationalizing")

        try:
            # Get findings from previous agent
            findings = state.get('findings', [])

            if not findings:
                # No findings to rationalize
                state['workflow_stage'] = 'styling'
                return state

            # Generate rationale for each finding
            for finding in findings:
                rationale = await self.generate_rationale(finding)

                if rationale:
                    # Add to context
                    state['neutral_rationales'].append(rationale)

            # Update workflow stage
            state['workflow_stage'] = 'styling'

        except Exception as e:
            state = log_error_to_context(state, "NeutralRationaleAgent", e)

        return state

    async def generate_rationale(self, finding: Dict) -> Optional[Dict]:
        """
        Generate neutral rationale for a finding
        REQ-NR-001 to REQ-NR-005: Complete rationale generation

        Args:
            finding: Finding dict from Diligent Reviewer

        Returns:
            Neutral rationale dict or None if generation fails
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a neutral legal analyst. Your task is to explain contract deviations objectively.

**CRITICAL RULES - STRICT NEUTRALITY**:
1. Use ONLY descriptive language (indicative mood)
2. NO imperatives: never use "must", "should", "required", "mandatory"
3. NO hedging: never use "consider", "perhaps", "might", "recommend"
4. NO subjectives: never use "dangerous", "unacceptable", "critical"
5. Use only: "differs from", "exceeds", "missing", "contradicts", "is", "contains"
6. Every claim must cite evidence from the clause

**Return ONLY a JSON object** (no markdown, no code blocks):
{{
  "issue_summary": "One sentence objective description",
  "evidence_quote": "Exact quote from clause",
  "policy_reference": "policy_id from finding",
  "impact_explanation": "Objective explanation of how this differs from policy (2-3 sentences)",
  "proposed_change": {{
    "change_type": "value_update|text_replacement|clause_insertion|clause_deletion",
    "current": "current text or value or null",
    "proposed": "proposed text or value",
    "reasoning": "why this change aligns with policy (neutral language only)"
  }},
  "fallback_options": [
    {{
      "option_text": "alternative wording",
      "conditions": ["prerequisite 1", "prerequisite 2"],
      "risk_level": "low|medium|high"
    }}
  ]
}}

**Good Example**:
"This clause caps liability at 1× fees, which differs from Policy LP-401 requiring 2× minimum for vendor contracts."

**BAD Examples (NEVER DO THIS)**:
- "This clause MUST be revised" ❌
- "We SHOULD increase the cap" ❌
- "This is UNACCEPTABLE risk" ❌
- "Consider changing to 2×" ❌

Remember: Describe what IS, not what SHOULD BE."""),
            ("user", """Finding Details:
- Severity: {severity}
- Deviation Type: {deviation_type}
- Evidence: {evidence_quote}
- Policy Requirement: {policy_requirement}
- Explanation: {explanation}

Generate neutral rationale in JSON format:""")
        ])

        try:
            # Invoke Claude
            response = await self.llm.ainvoke(
                prompt.format(
                    severity=finding.get('severity', 'medium'),
                    deviation_type=finding.get('deviation_type', 'unknown'),
                    evidence_quote=finding.get('evidence_quote', ''),
                    policy_requirement=finding.get('policy_requirement', ''),
                    explanation=finding.get('explanation', '')
                )
            )

            # Parse response (handle markdown code blocks)
            content = response.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]  # Remove first line
                content = content.rsplit('\n```', 1)[0]  # Remove last line
            rationale_data = json.loads(content)

            # REQ-NR-004: Validate neutrality
            self._validate_neutrality(rationale_data)

            # REQ-NR-005: Validate schema
            self._validate_schema(rationale_data)

            # Create full rationale object
            rationale = {
                'rationale_id': str(uuid4()),
                'finding_id': finding['finding_id'],
                'schema_version': '1.0',
                'neutral_explanation': self._build_neutral_explanation(rationale_data),
                'proposed_change': rationale_data['proposed_change'],
                'fallback_options': rationale_data.get('fallback_options', []),
                'confidence_score': 0.95,
                'timestamp': datetime.utcnow().isoformat()
            }

            return rationale

        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON from LLM for finding {finding['finding_id']}")
            return None

        except ValueError as e:
            # Validation failed
            print(f"Warning: Validation failed for finding {finding['finding_id']}: {e}")
            return None

        except Exception as e:
            print(f"Error generating rationale for finding {finding['finding_id']}: {e}")
            return None

    def _validate_neutrality(self, rationale_data: Dict):
        """
        REQ-NR-004: Ensure no tone/aggressiveness in neutral rationale

        Args:
            rationale_data: Rationale dict to validate

        Raises:
            ValueError: If neutrality rules violated
        """
        # Convert all text to lowercase for checking
        full_text = json.dumps(rationale_data).lower()

        # Check for prohibited words
        found_prohibited = [word for word in self.PROHIBITED_WORDS if f' {word} ' in f' {full_text} ']

        if found_prohibited:
            raise ValueError(f"Neutral rationale contains prohibited words: {found_prohibited}")

        # Sentiment analysis - must be neutral (polarity between -0.1 and 0.1)
        impact_text = rationale_data.get('impact_explanation', '')
        if impact_text:
            blob = TextBlob(impact_text)
            polarity = blob.sentiment.polarity

            if abs(polarity) > 0.15:  # Allow slight leeway
                raise ValueError(f"Rationale sentiment not neutral: {polarity:.2f}")

    def _validate_schema(self, rationale_data: Dict):
        """
        REQ-NR-005: Validate against JSON schema

        Args:
            rationale_data: Rationale dict to validate

        Raises:
            ValueError: If schema validation fails
        """
        # Check required fields
        required_fields = [
            'issue_summary',
            'evidence_quote',
            'policy_reference',
            'impact_explanation',
            'proposed_change'
        ]

        for field in required_fields:
            if field not in rationale_data or not rationale_data[field]:
                raise ValueError(f"Missing required field: {field}")

        # Validate proposed_change structure
        change = rationale_data['proposed_change']
        required_change_fields = ['change_type', 'proposed', 'reasoning']

        for field in required_change_fields:
            if field not in change or not change[field]:
                raise ValueError(f"proposed_change missing field: {field}")

        # Validate change_type enum
        valid_change_types = ['value_update', 'text_replacement', 'clause_insertion', 'clause_deletion']
        if change['change_type'] not in valid_change_types:
            raise ValueError(f"Invalid change_type: {change['change_type']}")

        # Validate fallback_options if present
        if 'fallback_options' in rationale_data:
            for option in rationale_data['fallback_options']:
                required_option_fields = ['option_text', 'conditions', 'risk_level']
                for field in required_option_fields:
                    if field not in option:
                        raise ValueError(f"fallback_option missing field: {field}")

                # Validate risk_level enum
                if option['risk_level'] not in ['low', 'medium', 'high']:
                    raise ValueError(f"Invalid risk_level: {option['risk_level']}")

    def _build_neutral_explanation(self, rationale_data: Dict) -> str:
        """
        Construct full neutral explanation from components

        Args:
            rationale_data: Rationale dict

        Returns:
            Complete neutral explanation string
        """
        summary = rationale_data['issue_summary']
        impact = rationale_data['impact_explanation']

        return f"{summary} {impact}".strip()

    def get_stats(self, state: AnalysisContext) -> Dict:
        """
        Get statistics about rationales

        Args:
            state: Analysis context

        Returns:
            Stats dict
        """
        rationales = state.get('neutral_rationales', [])
        findings = state.get('findings', [])

        stats = {
            'total_rationales': len(rationales),
            'total_findings': len(findings),
            'coverage_rate': len(rationales) / max(len(findings), 1),
            'with_fallbacks': sum(
                1 for r in rationales
                if r.get('fallback_options') and len(r['fallback_options']) > 0
            ),
            'by_change_type': {}
        }

        # Count by change type
        for rationale in rationales:
            change_type = rationale.get('proposed_change', {}).get('change_type', 'unknown')
            stats['by_change_type'][change_type] = stats['by_change_type'].get(change_type, 0) + 1

        return stats
