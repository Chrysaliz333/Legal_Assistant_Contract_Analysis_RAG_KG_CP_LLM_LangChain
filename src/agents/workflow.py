"""
LangGraph Workflow Orchestrator
Coordinates all 4 agents in sequential pipeline:
1. Diligent Reviewer → finds policy deviations
2. Neutral Rationale → generates objective explanations
3. Personality → transforms based on style
4. Editor → creates track-change edits

Uses LangGraph StateGraph for orchestration with built-in:
- State management
- Error handling
- Checkpointing
- Observable execution
"""

from typing import Dict, List, Optional
from datetime import datetime
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import AnalysisContext, create_initial_context
from src.agents.diligent_reviewer import DiligentReviewerAgent
from src.agents.neutral_rationale import NeutralRationaleAgent
from src.agents.personality import PersonalityAgent
from src.agents.editor import EditorAgent


class ContractAnalysisWorkflow:
    """
    LangGraph-based workflow orchestrator for contract analysis

    Coordinates 4-agent pipeline with state management and checkpointing
    """

    def __init__(self, enable_checkpointing: bool = True):
        """
        Initialize workflow with agents

        Args:
            enable_checkpointing: Enable LangGraph checkpointing for resumability
        """
        # Initialize agents
        self.diligent_reviewer = DiligentReviewerAgent()
        self.neutral_rationale = NeutralRationaleAgent()
        self.personality = PersonalityAgent()
        self.editor = EditorAgent()

        # Build workflow graph
        self.workflow = self._build_workflow()

        # Compile with optional checkpointing
        if enable_checkpointing:
            checkpointer = MemorySaver()
            self.app = self.workflow.compile(checkpointer=checkpointer)
        else:
            self.app = self.workflow.compile()

    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph StateGraph connecting all agents

        Returns:
            StateGraph configured with agent nodes and edges
        """
        # Create graph with AnalysisContext as state
        workflow = StateGraph(AnalysisContext)

        # Add agent nodes
        workflow.add_node("review", self.diligent_reviewer.process)
        workflow.add_node("rationale", self.neutral_rationale.process)
        workflow.add_node("style", self.personality.process)
        workflow.add_node("edit", self.editor.process)

        # Define linear pipeline
        workflow.set_entry_point("review")
        workflow.add_edge("review", "rationale")
        workflow.add_edge("rationale", "style")
        workflow.add_edge("style", "edit")
        workflow.add_edge("edit", END)

        return workflow

    async def analyze_contract(
        self,
        version_id: str,
        session_id: str,
        contract_text: str,
        clauses: List[Dict],
        policies: List[Dict],
        style_params: Optional[Dict] = None,
        config: Optional[Dict] = None
    ) -> Dict:
        """
        Main entry point for contract analysis workflow

        Args:
            version_id: UUID of document version
            session_id: UUID of negotiation session
            contract_text: Full contract text
            clauses: List of extracted clauses (from user's extraction service)
            policies: List of applicable policies
            style_params: Optional personality settings (tone, formality, etc.)
            config: Optional LangGraph config (thread_id for checkpointing)

        Returns:
            Complete analysis result with findings, rationales, and edits
        """
        # Create initial context
        initial_state = create_initial_context(
            version_id=version_id,
            session_id=session_id,
            contract_text=contract_text,
            clauses=clauses,
            policies=policies,
            style_params=style_params
        )

        # Execute workflow
        final_state = await self.app.ainvoke(initial_state, config=config)

        # Build result summary
        result = {
            'version_id': version_id,
            'session_id': session_id,
            'workflow_stage': final_state['workflow_stage'],
            'analysis_summary': self._build_summary(final_state),
            'findings': final_state.get('findings', []),
            'neutral_rationales': final_state.get('neutral_rationales', []),
            'transformed_rationales': final_state.get('transformed_rationales', []),
            'suggested_edits': final_state.get('suggested_edits', []),
            'errors': final_state.get('errors', []),
            'metadata': {
                'started_at': final_state.get('started_at'),
                'completed_at': final_state.get('updated_at'),
                'current_agent': final_state.get('current_agent')
            }
        }

        return result

    async def analyze_contract_streaming(
        self,
        version_id: str,
        session_id: str,
        contract_text: str,
        clauses: List[Dict],
        policies: List[Dict],
        style_params: Optional[Dict] = None,
        config: Optional[Dict] = None
    ):
        """
        Stream workflow execution with intermediate state updates

        Args:
            version_id: UUID of document version
            session_id: UUID of negotiation session
            contract_text: Full contract text
            clauses: List of extracted clauses
            policies: List of applicable policies
            style_params: Optional personality settings
            config: Optional LangGraph config

        Yields:
            State updates after each agent completes
        """
        # Create initial context
        initial_state = create_initial_context(
            version_id=version_id,
            session_id=session_id,
            contract_text=contract_text,
            clauses=clauses,
            policies=policies,
            style_params=style_params
        )

        # Stream workflow execution
        async for state in self.app.astream(initial_state, config=config):
            # state is dict with node name as key
            # e.g., {"review": {...updated_state...}}

            # Yield the updated state
            for node_name, updated_state in state.items():
                yield {
                    'node': node_name,
                    'stage': updated_state.get('workflow_stage'),
                    'current_agent': updated_state.get('current_agent'),
                    'findings_count': len(updated_state.get('findings', [])),
                    'rationales_count': len(updated_state.get('neutral_rationales', [])),
                    'transformations_count': len(updated_state.get('transformed_rationales', [])),
                    'edits_count': len(updated_state.get('suggested_edits', [])),
                    'errors': updated_state.get('errors', [])
                }

    def _build_summary(self, state: AnalysisContext) -> Dict:
        """
        Build high-level summary of analysis results

        Args:
            state: Final analysis context

        Returns:
            Summary dict with key metrics
        """
        findings = state.get('findings', [])
        rationales = state.get('neutral_rationales', [])
        edits = state.get('suggested_edits', [])

        # Count by severity
        severity_counts = {}
        for finding in findings:
            severity = finding.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count conflicts
        conflict_count = sum(
            1 for edit in edits
            if edit.get('conflicts_with')
        )

        summary = {
            'total_findings': len(findings),
            'total_rationales': len(rationales),
            'total_edits': len(edits),
            'by_severity': severity_counts,
            'critical_count': severity_counts.get('critical', 0),
            'high_count': severity_counts.get('high', 0),
            'edits_with_conflicts': conflict_count,
            'style_params': state.get('style_params', {}),
            'has_errors': len(state.get('errors', [])) > 0
        }

        return summary

    async def resume_workflow(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Dict:
        """
        Resume workflow from checkpoint

        Args:
            thread_id: Thread ID from previous execution
            checkpoint_id: Optional specific checkpoint to resume from

        Returns:
            Resumed workflow result
        """
        config = {"configurable": {"thread_id": thread_id}}

        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id

        # Resume from checkpoint
        final_state = await self.app.ainvoke(None, config=config)

        return {
            'version_id': final_state.get('version_id'),
            'workflow_stage': final_state['workflow_stage'],
            'analysis_summary': self._build_summary(final_state),
            'suggested_edits': final_state.get('suggested_edits', [])
        }

    def get_workflow_stats(self, state: AnalysisContext) -> Dict:
        """
        Get detailed statistics from all agents

        Args:
            state: Analysis context

        Returns:
            Combined stats from all agents
        """
        stats = {
            'diligent_reviewer': self.diligent_reviewer.get_stats(state),
            'neutral_rationale': self.neutral_rationale.get_stats(state),
            'personality': self.personality.get_stats(state),
            'editor': self.editor.get_stats(state),
            'overall': self._build_summary(state)
        }

        return stats


# Convenience function for single contract analysis
async def analyze_contract(
    version_id: str,
    session_id: str,
    contract_text: str,
    clauses: List[Dict],
    policies: List[Dict],
    style_params: Optional[Dict] = None,
    enable_streaming: bool = False
) -> Dict:
    """
    Analyze a contract through the complete 4-agent pipeline

    Args:
        version_id: UUID of document version
        session_id: UUID of negotiation session
        contract_text: Full contract text
        clauses: List of extracted clauses (from user's extraction service)
        policies: List of applicable policies
        style_params: Optional personality settings
        enable_streaming: Return streaming generator instead of final result

    Returns:
        Analysis result with findings, rationales, and suggested edits
        OR async generator yielding intermediate states if enable_streaming=True

    Example:
        >>> result = await analyze_contract(
        ...     version_id="abc-123",
        ...     session_id="def-456",
        ...     contract_text="Full contract text...",
        ...     clauses=[{"clause_id": "...", "clause_text": "...", ...}],
        ...     policies=[{"policy_id": "...", "policy_text": "...", ...}],
        ...     style_params={"tone": "concise", "audience": "internal"}
        ... )
        >>> print(f"Found {len(result['findings'])} issues")
        >>> print(f"Generated {len(result['suggested_edits'])} edits")
    """
    workflow = ContractAnalysisWorkflow(enable_checkpointing=not enable_streaming)

    if enable_streaming:
        # Return streaming generator
        return workflow.analyze_contract_streaming(
            version_id=version_id,
            session_id=session_id,
            contract_text=contract_text,
            clauses=clauses,
            policies=policies,
            style_params=style_params
        )
    else:
        # Return final result
        return await workflow.analyze_contract(
            version_id=version_id,
            session_id=session_id,
            contract_text=contract_text,
            clauses=clauses,
            policies=policies,
            style_params=style_params
        )


# Batch analysis function
async def analyze_contracts_batch(
    contracts: List[Dict],
    policies: List[Dict],
    style_params: Optional[Dict] = None,
    max_concurrent: int = 5
) -> List[Dict]:
    """
    Analyze multiple contracts in parallel

    Args:
        contracts: List of contract dicts with version_id, session_id, text, clauses
        policies: Shared policies to check against
        style_params: Optional shared personality settings
        max_concurrent: Maximum number of concurrent analyses

    Returns:
        List of analysis results
    """
    import asyncio

    workflow = ContractAnalysisWorkflow(enable_checkpointing=False)

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze_with_semaphore(contract):
        async with semaphore:
            return await workflow.analyze_contract(
                version_id=contract['version_id'],
                session_id=contract['session_id'],
                contract_text=contract['contract_text'],
                clauses=contract['clauses'],
                policies=policies,
                style_params=style_params
            )

    # Execute all analyses in parallel (with concurrency limit)
    results = await asyncio.gather(*[
        analyze_with_semaphore(contract)
        for contract in contracts
    ])

    return results
