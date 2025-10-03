"""
Unified Contract Review Agent
Replaces the flawed 4-agent pipeline with a single context-aware agent

Key improvements:
- Full contract context (no isolated clause analysis)
- Policy application only where relevant (no over-application)
- Evidence extracted from CONTRACT, not policy text
- Direct edit generation in single pass
- Memory for personality consistency
"""

from typing import Dict, List, Optional
from datetime import datetime
import json

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from config.settings import settings


class UnifiedContractAgent:
    """
    Single agent that replaces DiligentReviewer + NeutralRationale + Personality + Editor

    Workflow:
    1. Read entire contract with full context
    2. Identify policy violations (only where genuinely applicable)
    3. Extract evidence from CONTRACT text (not policy text)
    4. Generate specific, actionable edits with track-changes
    5. Apply personality/style in same pass (no separate transformation)
    """

    def __init__(self, style_params: Optional[Dict] = None):
        """
        Initialize agent with personality settings

        Args:
            style_params: Optional style configuration (tone, formality, aggressiveness, audience)
        """
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Use full GPT-4o for better reasoning
            max_tokens=4096,  # Need space for full contract + analysis
            temperature=0.2,  # Low temp for consistency
            timeout=60,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Default style params
        self.style_params = style_params or {
            'tone': 'balanced',
            'formality': 'legal',
            'aggressiveness': 'balanced',
            'audience': 'internal'
        }

    async def analyze_contract(
        self,
        contract_text: str,
        policies: List[Dict],
        clause_metadata: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Perform complete contract analysis in single pass

        Args:
            contract_text: Full contract text
            policies: List of policy dicts with policy_id, title, requirement
            clause_metadata: Optional pre-extracted clause boundaries

        Returns:
            Analysis result with findings and suggested edits
        """
        # Build comprehensive system prompt with personality
        system_prompt = self._build_system_prompt()

        # Build user prompt with contract and policies
        user_prompt = self._build_user_prompt(contract_text, policies, clause_metadata)

        # Single LLM call with full context
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        # Parse structured response
        try:
            result = json.loads(response.content)

            # Add metadata
            result['analysis_metadata'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'style_params': self.style_params,
                'model': 'gpt-4o',
                'contract_length': len(contract_text),
                'policies_checked': len(policies)
            }

            return result

        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return {
                'findings': [],
                'suggested_edits': [],
                'error': 'Failed to parse LLM response',
                'raw_response': response.content
            }

    def _build_system_prompt(self) -> str:
        """Build system prompt with personality and instructions"""

        # Get style instructions
        tone = self._get_tone_instruction(self.style_params['tone'])
        formality = self._get_formality_instruction(self.style_params['formality'])
        aggressiveness = self._get_aggressiveness_instruction(self.style_params['aggressiveness'])
        audience = self._get_audience_instruction(self.style_params['audience'])

        return f"""You are an expert contract review agent for a legal team.

**YOUR PERSONALITY & COMMUNICATION STYLE:**

{tone}

{formality}

{aggressiveness}

{audience}

**YOUR TASK:**
Analyze the contract below against the provided policies. For each violation:

1. **Quote the CONTRACT text** (not policy text) as evidence
2. **Apply policies only where genuinely relevant** (don't force-fit every policy to every clause)
3. **Consider full contract context** (how clauses relate to each other)
4. **Generate specific edits** in track-change format with exact wording

**CRITICAL RULES:**
- Evidence MUST be exact quotes from the CONTRACT (not from policy documents)
- Only flag violations where the policy clearly applies to that clause type
- Each suggested edit must specify:
  - Exact text to delete (with character positions)
  - Exact text to insert
  - Clear rationale tied to policy requirement

**OUTPUT FORMAT:**
Return ONLY a JSON object (no markdown, no code blocks):

{{
  "findings": [
    {{
      "finding_id": "unique_id",
      "clause_reference": "Section X.Y or paragraph number",
      "policy_violated": "policy_id (e.g., LP-401)",
      "severity": "critical|high|medium|low",
      "contract_evidence": "EXACT QUOTE FROM CONTRACT",
      "issue_explanation": "What's wrong and why (in YOUR communication style)",
      "suggested_edit": {{
        "change_type": "value_update|text_replacement|clause_insertion|clause_deletion",
        "current_text": "exact current wording from contract",
        "proposed_text": "exact proposed wording",
        "track_changes": {{
          "deletions": [{{"start": 0, "end": 10, "text": "old text"}}],
          "insertions": [{{"position": 10, "text": "new text"}}]
        }},
        "rationale": "Why this change aligns with policy (in YOUR style)"
      }},
      "fallback_options": [
        {{
          "alternative_text": "alternative wording",
          "conditions": ["when this alternative is acceptable"],
          "risk_level": "low|medium|high"
        }}
      ]
    }}
  ],
  "summary": {{
    "total_findings": 0,
    "by_severity": {{"critical": 0, "high": 0, "medium": 0, "low": 0}},
    "total_suggested_edits": 0,
    "key_themes": ["list of recurring issues"]
  }}
}}

Be thorough but focused. Quality over quantity."""

    def _build_user_prompt(
        self,
        contract_text: str,
        policies: List[Dict],
        clause_metadata: Optional[List[Dict]]
    ) -> str:
        """Build user prompt with contract and context"""

        # Format policies
        policy_list = "\n".join([
            f"- {p['policy_id']}: {p['title']} - {p['requirement']}"
            for p in policies
        ])

        # Add clause metadata if available
        clause_context = ""
        if clause_metadata:
            clause_context = "\n**Clause Boundaries (for reference):**\n"
            clause_context += "\n".join([
                f"- {c.get('clause_type', 'unknown')}: Line {c.get('start_line', '?')}-{c.get('end_line', '?')}"
                for c in clause_metadata[:10]  # Show first 10
            ])
            if len(clause_metadata) > 10:
                clause_context += f"\n- ... and {len(clause_metadata) - 10} more clauses"

        return f"""**POLICIES TO CHECK:**

{policy_list}

{clause_context}

**CONTRACT TEXT:**

{contract_text}

---

Analyze the contract above. Return JSON with findings and suggested edits."""

    def _get_tone_instruction(self, tone: str) -> str:
        """Get tone-specific instructions"""
        if tone == "concise":
            return "**TONE: Concise** - Maximum 50 words per explanation. Direct, brief statements."
        elif tone == "verbose":
            return "**TONE: Verbose** - Comprehensive explanations (200-500 words). Include context, reasoning, and implications."
        else:  # balanced
            return "**TONE: Balanced** - Clear explanations with essential context (100-200 words)."

    def _get_formality_instruction(self, formality: str) -> str:
        """Get formality-specific instructions"""
        if formality == "legal":
            return "**FORMALITY: Legal/Technical** - Use precise legal terminology, formal sentence structure, citations."
        else:  # plain_english
            return "**FORMALITY: Plain English** - Conversational but professional. Avoid legalese. Use analogies."

    def _get_aggressiveness_instruction(self, aggressiveness: str) -> str:
        """Get aggressiveness-specific instructions"""
        if aggressiveness == "strict":
            return "**AGGRESSIVENESS: Strict** - Use mandatory language: 'must revise', 'required', 'non-negotiable'. No fallback options."
        elif aggressiveness == "flexible":
            return "**AGGRESSIVENESS: Flexible** - Use preference language: 'recommend', 'prefer', 'suggest'. Emphasize fallback options."
        else:  # balanced
            return "**AGGRESSIVENESS: Balanced** - Clear but not absolutist. Mention fallbacks but don't overemphasize."

    def _get_audience_instruction(self, audience: str) -> str:
        """Get audience-specific instructions"""
        if audience == "internal":
            return "**AUDIENCE: Internal Legal Team** - Use legal abbreviations (LoL, IP, SLA). Reference internal policy IDs directly."
        else:  # counterparty
            return "**AUDIENCE: Counterparty/External** - Spell out abbreviations. No internal policy IDs. Professional but accessible."

    def get_stats(self, analysis_result: Dict) -> Dict:
        """Extract statistics from analysis result"""
        findings = analysis_result.get('findings', [])

        return {
            'total_findings': len(findings),
            'with_edits': sum(1 for f in findings if f.get('suggested_edit')),
            'by_severity': {
                'critical': sum(1 for f in findings if f.get('severity') == 'critical'),
                'high': sum(1 for f in findings if f.get('severity') == 'high'),
                'medium': sum(1 for f in findings if f.get('severity') == 'medium'),
                'low': sum(1 for f in findings if f.get('severity') == 'low')
            },
            'style_params': self.style_params,
            'timestamp': analysis_result.get('analysis_metadata', {}).get('timestamp')
        }
