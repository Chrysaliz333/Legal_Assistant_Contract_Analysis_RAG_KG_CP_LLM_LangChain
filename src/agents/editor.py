"""
Editor Agent
REQ-SE-001: Track-Change Format Generation
REQ-SE-002: Policy Anchoring for Each Edit
REQ-SE-003: Conflict Detection (overlapping edits)
REQ-SE-004: Accept/Reject Workflow Support
REQ-SE-005: Redlining Export (Word, PDF)
"""

from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime
import json
import re

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from config.settings import settings
from src.agents.state import AnalysisContext, update_context_metadata, log_error_to_context


class EditorAgent:
    """
    Editor Agent - Fourth and final stage of analysis

    Responsibilities:
    - Generate track-change format suggested edits
    - Anchor each edit to policy requirements
    - Detect conflicts between overlapping edits
    - Prepare edits for accept/reject workflow
    - Support redlining export
    """

    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=settings.CLAUDE_TEMPERATURE,
            timeout=settings.CLAUDE_TIMEOUT,
            anthropic_api_key=settings.ANTHROPIC_API_KEY
        )

    async def process(self, state: AnalysisContext) -> AnalysisContext:
        """
        Main entry point for agent processing

        Args:
            state: Current analysis context with transformed_rationales

        Returns:
            Updated context with suggested_edits added
        """
        # Update metadata
        state = update_context_metadata(state, "EditorAgent", "editing")

        try:
            # Get transformed rationales from previous agent
            transformed_rationales = state.get('transformed_rationales', [])

            if not transformed_rationales:
                # No rationales to convert to edits
                state['workflow_stage'] = 'complete'
                return state

            # Get corresponding neutral rationales and findings for context
            neutral_rationales = state.get('neutral_rationales', [])
            findings = state.get('findings', [])
            clauses = state.get('clauses', [])

            # Create lookup dictionaries
            neutral_by_id = {r['rationale_id']: r for r in neutral_rationales}
            findings_by_id = {f['finding_id']: f for f in findings}
            clauses_by_id = {c['clause_id']: c for c in clauses}

            # Generate edits for each transformed rationale
            suggested_edits = []
            for transformation in transformed_rationales:
                # Get neutral rationale and finding
                neutral = neutral_by_id.get(transformation['rationale_id'])
                if not neutral:
                    continue

                finding = findings_by_id.get(neutral['finding_id'])
                if not finding:
                    continue

                # Get the clause being edited
                clause = clauses_by_id.get(finding.get('clause_id'))
                if not clause:
                    continue

                # Generate suggested edit
                edit = await self.generate_edit(
                    transformation=transformation,
                    neutral_rationale=neutral,
                    finding=finding,
                    clause=clause
                )

                if edit:
                    suggested_edits.append(edit)

            # REQ-SE-003: Detect conflicts between edits
            suggested_edits = self._detect_conflicts(suggested_edits)

            # Add to context
            state['suggested_edits'] = suggested_edits

            # Update workflow stage
            state['workflow_stage'] = 'complete'

        except Exception as e:
            state = log_error_to_context(state, "EditorAgent", e)

        return state

    async def generate_edit(
        self,
        transformation: Dict,
        neutral_rationale: Dict,
        finding: Dict,
        clause: Dict
    ) -> Optional[Dict]:
        """
        Generate suggested edit in track-change format
        REQ-SE-001: Track-change format with deletions and insertions
        REQ-SE-002: Policy anchoring

        Args:
            transformation: Transformed rationale from Personality Agent
            neutral_rationale: Neutral rationale from Neutral Rationale Agent
            finding: Finding from Diligent Reviewer
            clause: Original clause being edited

        Returns:
            Suggested edit dict or None if generation fails
        """
        # Get proposed change from neutral rationale
        proposed_change = neutral_rationale['proposed_change']

        # Build prompt for track-change generation
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a legal document editor. Generate precise track-change format edits.

**Your Task**: Convert the proposed change into track-change format with exact character positions.

**Track-Change Format**:
- Deletions: text to be removed
- Insertions: text to be added
- Position: character offset in original clause

**Return ONLY a JSON object** (no markdown, no code blocks):
{{
  "edit_type": "value_change|text_replacement|clause_insertion|clause_deletion",
  "deletions": [
    {{
      "start_char": 0,
      "end_char": 10,
      "deleted_text": "text being removed"
    }}
  ],
  "insertions": [
    {{
      "position_char": 10,
      "inserted_text": "text being added"
    }}
  ],
  "resulting_text": "full clause text after applying all changes",
  "change_summary": "brief description (e.g., 'Change liability cap from 1× to 2× annual fees')"
}}

**Rules**:
1. Positions must be exact character offsets
2. Deletions come before insertions
3. resulting_text must be the complete modified clause
4. For clause_insertion, entire clause goes in insertions[0]
5. For clause_deletion, entire clause goes in deletions[0]

Be precise with character positions. They will be used for programmatic edits."""),
            ("user", """Original Clause Text:
{clause_text}

Change Type: {change_type}
Current Value: {current}
Proposed Value: {proposed}
Reasoning: {reasoning}

Generate track-change format JSON:""")
        ])

        try:
            # Invoke Claude
            response = await self.llm.ainvoke(
                prompt.format(
                    clause_text=clause['clause_text'],
                    change_type=proposed_change['change_type'],
                    current=json.dumps(proposed_change.get('current')),
                    proposed=json.dumps(proposed_change['proposed']),
                    reasoning=proposed_change['reasoning']
                )
            )

            # Parse response (handle markdown code blocks)
            content = response.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]  # Remove first line
                content = content.rsplit('\n```', 1)[0]  # Remove last line
            edit_data = json.loads(content)

            # REQ-SE-001 & REQ-SE-002: Create structured edit with policy anchor
            suggested_edit = {
                'edit_id': str(uuid4()),
                'finding_id': finding['finding_id'],
                'rationale_id': neutral_rationale['rationale_id'],
                'transformation_id': transformation['transformation_id'],
                'clause_id': clause['clause_id'],

                # Track-change data (REQ-SE-001)
                'edit_type': edit_data['edit_type'],
                'deletions': edit_data.get('deletions', []),
                'insertions': edit_data.get('insertions', []),
                'resulting_text': edit_data['resulting_text'],
                'change_summary': edit_data['change_summary'],

                # Policy anchoring (REQ-SE-002)
                'policy_anchor': {
                    'policy_id': finding['policy_id'],
                    'policy_requirement': finding['policy_requirement'],
                    'deviation_type': finding['deviation_type'],
                    'severity': finding['severity']
                },

                # Styled explanation for display
                'explanation': transformation['transformed_text'],

                # Workflow support (REQ-SE-004)
                'status': 'pending',  # pending|accepted|rejected
                'applied_at': None,
                'applied_by': None,
                'rejection_reason': None,

                # Conflict detection placeholder (REQ-SE-003)
                'conflicts_with': [],

                # Metadata
                'timestamp': datetime.utcnow().isoformat()
            }

            return suggested_edit

        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON from LLM for edit generation: {e}")
            return None

        except Exception as e:
            print(f"Error generating edit: {e}")
            return None

    def _detect_conflicts(self, edits: List[Dict]) -> List[Dict]:
        """
        REQ-SE-003: Detect conflicts between overlapping edits

        Conflicts occur when:
        - Two edits target the same clause
        - Their character ranges overlap
        - Both edits modify/delete overlapping text

        Args:
            edits: List of suggested edits

        Returns:
            Edits with conflicts_with field populated
        """
        # Group edits by clause_id
        by_clause = {}
        for edit in edits:
            clause_id = edit['clause_id']
            if clause_id not in by_clause:
                by_clause[clause_id] = []
            by_clause[clause_id].append(edit)

        # Check for conflicts within each clause
        for clause_id, clause_edits in by_clause.items():
            if len(clause_edits) <= 1:
                continue  # No conflicts possible

            # Compare each pair
            for i, edit1 in enumerate(clause_edits):
                for edit2 in clause_edits[i+1:]:
                    if self._edits_overlap(edit1, edit2):
                        # Mark conflict
                        edit1['conflicts_with'].append(edit2['edit_id'])
                        edit2['conflicts_with'].append(edit1['edit_id'])

        return edits

    def _edits_overlap(self, edit1: Dict, edit2: Dict) -> bool:
        """
        Check if two edits have overlapping character ranges

        Args:
            edit1: First edit
            edit2: Second edit

        Returns:
            True if edits overlap
        """
        # Get character ranges for each edit
        ranges1 = self._get_edit_ranges(edit1)
        ranges2 = self._get_edit_ranges(edit2)

        # Check if any ranges overlap
        for start1, end1 in ranges1:
            for start2, end2 in ranges2:
                # Overlap if one range starts before the other ends
                if not (end1 <= start2 or end2 <= start1):
                    return True

        return False

    def _get_edit_ranges(self, edit: Dict) -> List[Tuple[int, int]]:
        """
        Get all character ranges affected by an edit

        Args:
            edit: Suggested edit

        Returns:
            List of (start, end) tuples
        """
        ranges = []

        # Add deletion ranges
        for deletion in edit.get('deletions', []):
            ranges.append((deletion['start_char'], deletion['end_char']))

        # Add insertion positions (treat as single character range)
        for insertion in edit.get('insertions', []):
            pos = insertion['position_char']
            ranges.append((pos, pos + 1))

        return ranges

    def apply_edit(
        self,
        clause_text: str,
        edit: Dict
    ) -> str:
        """
        Apply a suggested edit to clause text
        REQ-SE-004: Support for accept workflow

        Args:
            clause_text: Original clause text
            edit: Suggested edit to apply

        Returns:
            Modified clause text
        """
        # Start with original text
        result = clause_text

        # Apply deletions (in reverse order to maintain positions)
        deletions = sorted(
            edit.get('deletions', []),
            key=lambda d: d['start_char'],
            reverse=True
        )

        for deletion in deletions:
            start = deletion['start_char']
            end = deletion['end_char']
            result = result[:start] + result[end:]

        # Apply insertions (in reverse order to maintain positions)
        insertions = sorted(
            edit.get('insertions', []),
            key=lambda i: i['position_char'],
            reverse=True
        )

        for insertion in insertions:
            pos = insertion['position_char']
            text = insertion['inserted_text']
            result = result[:pos] + text + result[pos:]

        return result

    def generate_redline_document(
        self,
        original_text: str,
        edits: List[Dict],
        format: str = 'html'
    ) -> str:
        """
        REQ-SE-005: Generate redline document showing all changes

        Args:
            original_text: Full contract text
            edits: List of suggested edits
            format: 'html' or 'markdown'

        Returns:
            Redline document with track changes visible
        """
        if format == 'html':
            return self._generate_html_redline(original_text, edits)
        elif format == 'markdown':
            return self._generate_markdown_redline(original_text, edits)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_redline(self, text: str, edits: List[Dict]) -> str:
        """
        Generate HTML redline with CSS styling

        Args:
            text: Original text
            edits: Suggested edits

        Returns:
            HTML string with track changes
        """
        # Sort edits by position (reverse order for application)
        sorted_edits = sorted(
            edits,
            key=lambda e: e['deletions'][0]['start_char'] if e.get('deletions') else 0,
            reverse=True
        )

        result = text

        for edit in sorted_edits:
            # Apply deletions with strikethrough
            for deletion in reversed(edit.get('deletions', [])):
                start = deletion['start_char']
                end = deletion['end_char']
                deleted_text = deletion['deleted_text']

                result = (
                    result[:start] +
                    f'<del style="color: red; text-decoration: line-through;">{deleted_text}</del>' +
                    result[end:]
                )

            # Apply insertions with underline
            for insertion in reversed(edit.get('insertions', [])):
                pos = insertion['position_char']
                inserted_text = insertion['inserted_text']

                result = (
                    result[:pos] +
                    f'<ins style="color: green; text-decoration: underline;">{inserted_text}</ins>' +
                    result[pos:]
                )

        # Wrap in HTML document
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Contract Redline</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; line-height: 1.6; padding: 2em; }}
        del {{ color: red; text-decoration: line-through; }}
        ins {{ color: green; text-decoration: underline; }}
        .clause {{ margin-bottom: 1em; }}
    </style>
</head>
<body>
    <h1>Contract with Track Changes</h1>
    <div class="content">
        {result}
    </div>
</body>
</html>"""

        return html

    def _generate_markdown_redline(self, text: str, edits: List[Dict]) -> str:
        """
        Generate Markdown redline

        Args:
            text: Original text
            edits: Suggested edits

        Returns:
            Markdown string with track changes
        """
        result = text

        # Sort edits by position (reverse order)
        sorted_edits = sorted(
            edits,
            key=lambda e: e['deletions'][0]['start_char'] if e.get('deletions') else 0,
            reverse=True
        )

        for edit in sorted_edits:
            # Apply deletions with strikethrough
            for deletion in reversed(edit.get('deletions', [])):
                start = deletion['start_char']
                end = deletion['end_char']
                deleted_text = deletion['deleted_text']

                result = result[:start] + f'~~{deleted_text}~~' + result[end:]

            # Apply insertions with bold
            for insertion in reversed(edit.get('insertions', [])):
                pos = insertion['position_char']
                inserted_text = insertion['inserted_text']

                result = result[:pos] + f'**{inserted_text}**' + result[pos:]

        # Add header
        markdown = f"""# Contract with Track Changes

## Legend
- ~~Strikethrough~~ = Deleted text
- **Bold** = Inserted text

---

{result}
"""

        return markdown

    def get_stats(self, state: AnalysisContext) -> Dict:
        """
        Get statistics about suggested edits

        Args:
            state: Analysis context

        Returns:
            Stats dict
        """
        edits = state.get('suggested_edits', [])

        stats = {
            'total_edits': len(edits),
            'by_type': {},
            'by_status': {},
            'with_conflicts': sum(1 for e in edits if e.get('conflicts_with')),
            'pending': sum(1 for e in edits if e.get('status') == 'pending'),
            'accepted': sum(1 for e in edits if e.get('status') == 'accepted'),
            'rejected': sum(1 for e in edits if e.get('status') == 'rejected')
        }

        # Count by edit type
        for edit in edits:
            edit_type = edit.get('edit_type', 'unknown')
            stats['by_type'][edit_type] = stats['by_type'].get(edit_type, 0) + 1

        # Count by status
        for edit in edits:
            status = edit.get('status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

        return stats
