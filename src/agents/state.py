"""
Shared state definition for multi-agent workflow
Uses LangGraph's TypedDict pattern for state management

REQ-ARCH-004: Multi-agent orchestration with shared context
"""

from typing import TypedDict, List, Dict, Optional, Annotated
from datetime import datetime
import operator


class AnalysisContext(TypedDict):
    """
    Shared context for contract analysis workflow

    This state is passed between all agents and accumulates results.
    Each agent reads from and writes to this shared context.

    The Annotated type with operator.add enables LangGraph to automatically
    merge list updates from concurrent or sequential agent executions.
    """

    # ============================================================================
    # INPUT (Set at workflow initialization)
    # ============================================================================

    version_id: str
    """UUID of document version being analyzed"""

    session_id: str
    """UUID of negotiation session"""

    contract_text: str
    """Full text of the contract"""

    clauses: List[Dict]
    """
    Extracted clauses with structure:
    {
        'clause_id': str,
        'clause_identifier': str,  # e.g., "5.1", "Limitation of Liability"
        'clause_type': str,        # e.g., "liability", "termination"
        'clause_text': str,
        'char_start': int,
        'char_end': int
    }
    """

    policies: List[Dict]
    """
    Relevant policies:
    {
        'policy_id': str,
        'policy_text': str,
        'policy_category': str,
        'policy_version': str
    }
    """

    style_params: Dict
    """
    Personality parameters:
    {
        'tone': 'concise' | 'verbose' | 'balanced',
        'formality': 'legal' | 'plain_english',
        'aggressiveness': 'strict' | 'balanced' | 'flexible',
        'audience': 'internal' | 'counterparty'
    }
    """

    # ============================================================================
    # AGENT OUTPUTS (Accumulated during workflow)
    # ============================================================================

    findings: List[Dict]
    """
    Findings from Diligent Reviewer (list grows with each finding):
    {
        'finding_id': str,
        'clause_id': str,
        'policy_id': str,
        'issue_type': str,
        'severity': str,
        'evidence_quote': str,
        'policy_requirement': str,
        'provenance': {...}
    }
    """

    neutral_rationales: List[Dict]
    """
    Neutral rationales from Neutral Rationale Agent:
    {
        'rationale_id': str,
        'finding_id': str,
        'neutral_explanation': str,
        'proposed_change': {...},
        'fallback_options': [...]
    }
    """

    transformed_rationales: List[Dict]
    """
    Styled rationales from Personality Agent:
    {
        'transformation_id': str,
        'rationale_id': str,
        'style_params': {...},
        'transformed_text': str
    }
    """

    suggested_edits: List[Dict]
    """
    Track-change edits from Editor Agent:
    {
        'edit_id': str,
        'clause_id': str,
        'finding_id': str,
        'edit_type': str,
        'suggested_text': str,
        'char_start': int,
        'char_end': int
    }
    """

    # ============================================================================
    # WORKFLOW METADATA
    # ============================================================================

    current_agent: str
    """Name of agent currently processing"""

    workflow_stage: str
    """Current stage: 'reviewing' | 'rationalizing' | 'styling' | 'editing' | 'complete'"""

    errors: Annotated[List[Dict], operator.add]
    """
    Any errors encountered:
    {
        'agent': str,
        'error_type': str,
        'message': str,
        'timestamp': str
    }
    """

    started_at: str
    """ISO 8601 timestamp when analysis started"""

    updated_at: str
    """ISO 8601 timestamp of last update"""


def create_initial_context(
    version_id: str,
    session_id: str,
    contract_text: str,
    clauses: List[Dict],
    policies: List[Dict],
    style_params: Optional[Dict] = None
) -> AnalysisContext:
    """
    Create initial context for workflow

    Args:
        version_id: Document version UUID
        session_id: Negotiation session UUID
        contract_text: Full contract text
        clauses: Extracted clauses
        policies: Applicable policies
        style_params: Optional personality settings (uses org defaults if None)

    Returns:
        Initial AnalysisContext ready for workflow
    """
    now = datetime.utcnow().isoformat()

    # Default style params if not provided (will be overridden by org/session defaults)
    default_style = {
        'tone': 'concise',
        'formality': 'legal',
        'aggressiveness': 'balanced',
        'audience': 'internal'
    }

    return AnalysisContext(
        # Input
        version_id=version_id,
        session_id=session_id,
        contract_text=contract_text,
        clauses=clauses,
        policies=policies,
        style_params=style_params or default_style,

        # Outputs (empty initially, will be populated by agents)
        findings=[],
        neutral_rationales=[],
        transformed_rationales=[],
        suggested_edits=[],

        # Metadata
        current_agent='initializing',
        workflow_stage='reviewing',
        errors=[],
        started_at=now,
        updated_at=now
    )


def update_context_metadata(
    state: AnalysisContext,
    agent_name: str,
    stage: Optional[str] = None
) -> AnalysisContext:
    """
    Helper to update context metadata

    Args:
        state: Current context
        agent_name: Name of agent updating context
        stage: Optional new workflow stage

    Returns:
        Updated context
    """
    state['current_agent'] = agent_name
    state['updated_at'] = datetime.utcnow().isoformat()

    if stage:
        state['workflow_stage'] = stage

    return state


def log_error_to_context(
    state: AnalysisContext,
    agent_name: str,
    error: Exception
) -> AnalysisContext:
    """
    Helper to log error to context

    Args:
        state: Current context
        agent_name: Name of agent where error occurred
        error: Exception that occurred

    Returns:
        Updated context with error logged
    """
    state['errors'].append({
        'agent': agent_name,
        'error_type': type(error).__name__,
        'message': str(error),
        'timestamp': datetime.utcnow().isoformat()
    })

    return state
