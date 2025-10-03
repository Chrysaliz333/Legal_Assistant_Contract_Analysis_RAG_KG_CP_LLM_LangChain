"""
Personality Agent
REQ-PA-001: Structured Rationale Persistence (transform without overwriting)
REQ-PA-002: Tone Control (concise vs verbose, formal vs plain-English)
REQ-PA-003: Aggressiveness Control (strict vs flexible)
REQ-PA-004: Audience Mode Switching (internal vs counterparty)
REQ-PA-005: Multi-Purpose Output (reuse across contexts)
REQ-PA-006: Default & Override Settings
REQ-PA-007: Consistency Across Versions
REQ-PA-008: Explainability (show neutral + styled side-by-side)
"""

from typing import Dict, Optional
from uuid import uuid4
from datetime import datetime
import json

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from config.settings import settings
from src.agents.state import AnalysisContext, update_context_metadata, log_error_to_context
from src.services.cache_service import cache_service


class PersonalityAgent:
    """
    Personality Agent - Third stage of analysis

    Responsibilities:
    - Transform neutral rationales based on personality settings
    - Apply tone (concise/verbose/balanced)
    - Apply formality (legal/plain_english)
    - Apply aggressiveness (strict/flexible)
    - Apply audience mode (internal/counterparty)
    - Cache transformations for reuse
    - Preserve original neutral rationale
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=settings.CLAUDE_TEMPERATURE,
            timeout=30,
            openai_api_key=settings.OPENAI_API_KEY
        )

    async def process(self, state: AnalysisContext) -> AnalysisContext:
        """
        Main entry point for agent processing

        Args:
            state: Current analysis context with neutral_rationales

        Returns:
            Updated context with transformed_rationales added
        """
        # Update metadata
        state = update_context_metadata(state, "PersonalityAgent", "styling")

        try:
            # Get neutral rationales from previous agent
            neutral_rationales = state.get('neutral_rationales', [])

            if not neutral_rationales:
                # No rationales to transform
                state['workflow_stage'] = 'editing'
                return state

            # Get style parameters from context
            style_params = state['style_params']

            # Get corresponding findings for context
            findings = state.get('findings', [])
            findings_by_id = {f['finding_id']: f for f in findings}

            # Process rationales in parallel
            import asyncio

            async def process_one(rationale):
                finding = findings_by_id.get(rationale['finding_id'])
                cached = await cache_service.get_transformation(rationale['rationale_id'], style_params)
                if cached:
                    return cached
                transformation = await self.transform_rationale(rationale, style_params, finding)
                if transformation:
                    await cache_service.set_transformation(rationale['rationale_id'], style_params, transformation)
                return transformation

            tasks = [process_one(r) for r in neutral_rationales]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if result and not isinstance(result, Exception):
                    state['transformed_rationales'].append(result)

            # Update workflow stage
            state['workflow_stage'] = 'editing'

        except Exception as e:
            state = log_error_to_context(state, "PersonalityAgent", e)

        return state

    async def transform_rationale(
        self,
        neutral_rationale: Dict,
        style_params: Dict,
        finding: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Transform neutral rationale based on style parameters
        REQ-PA-002 to REQ-PA-004: Apply all style transformations

        Args:
            neutral_rationale: Neutral rationale from previous agent
            style_params: Style parameters dict
            finding: Associated finding for additional context

        Returns:
            Transformation dict or None if generation fails
        """
        # Build prompt based on style parameters
        prompt = self._build_transformation_prompt(style_params)

        try:
            # Invoke Claude
            response = await self.llm.ainvoke(
                prompt.format(
                    neutral_explanation=neutral_rationale['neutral_explanation'],
                    proposed_change=json.dumps(neutral_rationale['proposed_change'], indent=2),
                    fallback_options=json.dumps(neutral_rationale.get('fallback_options', []), indent=2),
                    severity=finding.get('severity', 'medium') if finding else 'medium'
                )
            )

            # Create transformation record
            transformation = {
                'transformation_id': str(uuid4()),
                'rationale_id': neutral_rationale['rationale_id'],
                'style_params': style_params.copy(),
                'transformed_text': response.content.strip(),
                'timestamp': datetime.utcnow().isoformat()
            }

            return transformation

        except Exception as e:
            print(f"Error transforming rationale {neutral_rationale['rationale_id']}: {e}")
            return None

    def _build_transformation_prompt(self, style_params: Dict) -> ChatPromptTemplate:
        """
        Build prompt based on style parameters
        REQ-PA-002 to REQ-PA-004: Combine all style instructions

        Args:
            style_params: Style parameters dict

        Returns:
            ChatPromptTemplate configured for these style params
        """
        # Get individual style instructions
        tone_instruction = self._get_tone_instruction(style_params.get('tone', 'concise'))
        formality_instruction = self._get_formality_instruction(style_params.get('formality', 'legal'))
        aggressiveness_instruction = self._get_aggressiveness_instruction(style_params.get('aggressiveness', 'balanced'))
        audience_instruction = self._get_audience_instruction(style_params.get('audience', 'internal'))

        # Combine into system message
        system_message = f"""You are transforming neutral legal analysis into a specific communication style.

{tone_instruction}

{formality_instruction}

{aggressiveness_instruction}

{audience_instruction}

**Your Task**:
Transform the neutral explanation below according to these style guidelines.
- Maintain factual accuracy
- Do not add information not present in the source
- Apply the style guidelines consistently
- Return ONLY the transformed text (no preamble, no JSON)

Transform the following:"""

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", """**Neutral Explanation**:
{neutral_explanation}

**Proposed Change**:
{proposed_change}

**Fallback Options**:
{fallback_options}

**Finding Severity**: {severity}

Transform according to the style guidelines above:""")
        ])

    def _get_tone_instruction(self, tone: str) -> str:
        """REQ-PA-002: Tone control instructions"""

        if tone == "concise":
            return """**TONE: Concise**
- Maximum 50 words per rationale
- Direct, brief statements
- No elaboration unless critical
- Focus on key point only
- Example: "Clause caps liability at 1× fees. Policy requires 2×. Change to 2× annual fees."
"""
        elif tone == "verbose":
            return """**TONE: Verbose**
- Maximum 500 words
- Include comprehensive context and reasoning
- Explain policy rationale and implications
- Reference legal precedents where relevant
- Provide thorough explanation
- Example: "The limitation of liability clause in Section 5.2 establishes a liability cap at 1× annual fees. This deviates from organizational Policy LP-401, which mandates a minimum 2× multiplier for all vendor contracts. The policy basis stems from risk analysis indicating that 1× caps provide insufficient protection for the types of services typically procured..."
"""
        else:  # balanced
            return """**TONE: Balanced**
- 100-200 words
- Clear explanation with essential context
- Brief policy reference
- Balanced detail level
- Example: "This clause caps liability at 1× annual fees, which differs from Policy LP-401 requiring 2× minimum for vendor contracts. The 2× standard provides appropriate risk coverage for vendor relationships. Recommend changing the cap to 2× annual fees."
"""

    def _get_formality_instruction(self, formality: str) -> str:
        """REQ-PA-002: Formality control"""

        if formality == "legal":
            return """**FORMALITY: Legal/Technical**
- Use precise legal terminology
- Formal sentence structure
- Include citations and references
- Professional legal language
- Example: "The aforesaid limitation of liability provision contained in Section 5.2 herein establishes a cap of one times (1×) annual fees, which represents a deviation from the requirements set forth in Policy LP-401..."
"""
        else:  # plain_english
            return """**FORMALITY: Plain English**
- Conversational but professional tone
- Avoid legalese where possible
- Use analogies to clarify concepts
- Business-friendly language
- Example: "The liability cap in Section 5.2 is set at 1× annual fees. Think of this as insurance - the policy only covers the cost of one year's fees if something goes wrong. Our standard requires 2× coverage to better protect the organization..."
"""

    def _get_aggressiveness_instruction(self, aggressiveness: str) -> str:
        """REQ-PA-003: Aggressiveness control"""

        if aggressiveness == "strict":
            return """**AGGRESSIVENESS: Strict**
- Use mandatory language: "must revise", "required edit", "non-negotiable"
- Present as firm requirement with no flexibility
- DO NOT mention fallback options
- Position: "This change is required for approval"
- Example: "This clause must be revised to increase the liability cap to 2× annual fees as required by Policy LP-401. This change is non-negotiable for vendor agreements."
"""
        elif aggressiveness == "flexible":
            return """**AGGRESSIVENESS: Flexible**
- Use preference language: "recommend", "prefer", "suggest considering"
- Present fallback options prominently
- Collaborative, open to negotiation
- Position: "We prefer X, but Y is acceptable under conditions Z"
- Example: "We recommend increasing the liability cap to 2× annual fees per Policy LP-401. However, we would consider 1.5× if additional insurance coverage is provided. We're open to discussing alternative risk mitigation approaches."
"""
        else:  # balanced
            return """**AGGRESSIVENESS: Balanced**
- Use clear but not absolutist language
- Mention fallbacks if available but don't overemphasize
- Professional negotiation stance
- Position: "This change aligns with policy. Alternatives exist under specific conditions."
- Example: "The liability cap should be increased to 2× annual fees to align with Policy LP-401. Alternative arrangements may be considered if they provide equivalent risk protection."
"""

    def _get_audience_instruction(self, audience: str) -> str:
        """REQ-PA-004: Audience mode switching"""

        if audience == "internal":
            return """**AUDIENCE: Internal Legal Team**
- Use legal abbreviations: LoL, IP, SLA, NDA, etc.
- Reference internal policy IDs directly (e.g., "LP-401", "IP-203")
- Use internal shorthand and terminology
- Include technical legal details
- Example: "LoL cap at 1× (Policy LP-401 requires 2× for vendor). Recommend revision per standard playbook guidelines."
"""
        else:  # counterparty
            return """**AUDIENCE: Counterparty/External Counsel**
- Spell out ALL abbreviations
- No internal policy IDs (describe policies instead)
- Plain English where possible
- Business context over legal jargon
- Professional but accessible
- Example: "The liability limitation is currently set at 1× annual fees. Our standard requirement for vendor agreements is 2× annual fees to ensure adequate risk coverage. We'd like to discuss increasing this cap to align with our standard terms."
"""

    def get_stats(self, state: AnalysisContext) -> Dict:
        """
        Get statistics about transformations

        Args:
            state: Analysis context

        Returns:
            Stats dict
        """
        transformed = state.get('transformed_rationales', [])
        neutral = state.get('neutral_rationales', [])

        stats = {
            'total_transformations': len(transformed),
            'total_neutral': len(neutral),
            'transformation_rate': len(transformed) / max(len(neutral), 1),
            'style_params': state.get('style_params', {})
        }

        return stats
