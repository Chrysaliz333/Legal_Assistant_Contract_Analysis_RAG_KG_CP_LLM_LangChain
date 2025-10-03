# Agent Context Management Design

## Overview

The multi-agent system requires a **shared context** that passes between agents in a structured workflow. This document defines the context management architecture using LangGraph's state management.

---

## Context Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Shared Analysis Context                   │
│  (Passed between all agents via LangGraph State)            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  1. Diligent Reviewer                                        │
│     INPUT:  contract_text, clauses, policies                 │
│     OUTPUT: findings (with severity, evidence)               │
│     ADDS TO CONTEXT: structured_findings[]                   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  2. Neutral Rationale Agent                                  │
│     INPUT:  findings (from step 1)                           │
│     OUTPUT: neutral_rationale for each finding               │
│     ADDS TO CONTEXT: neutral_rationales[]                    │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  3. Personality Agent                                        │
│     INPUT:  neutral_rationales, style_params                 │
│     OUTPUT: styled_rationales                                │
│     ADDS TO CONTEXT: transformed_rationales[]                │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  4. Editor Agent                                             │
│     INPUT:  findings, rationales, clauses                    │
│     OUTPUT: suggested_edits (track-change format)            │
│     ADDS TO CONTEXT: suggested_edits[]                       │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  Final Analysis Result
```

---

## Context State Schema

### Primary State Object

```python
from typing import TypedDict, List, Dict, Optional
from uuid import UUID

class AnalysisContext(TypedDict):
    """
    Shared context passed between agents
    Implements LangGraph State interface
    """

    # Input data (set at start)
    version_id: str
    session_id: str
    contract_text: str
    clauses: List[Dict]  # Extracted clauses with metadata
    policies: List[Dict]  # Relevant policies
    style_params: Dict   # Personality settings

    # Agent outputs (populated as workflow progresses)
    findings: List[Dict]           # From Diligent Reviewer
    neutral_rationales: List[Dict] # From Neutral Rationale Agent
    transformed_rationales: List[Dict]  # From Personality Agent
    suggested_edits: List[Dict]    # From Editor Agent

    # Metadata
    current_agent: str
    workflow_stage: str  # 'reviewing' | 'rationalizing' | 'styling' | 'editing' | 'complete'
    errors: List[Dict]
    started_at: str      # ISO 8601
    updated_at: str      # ISO 8601
```

---

## Implementation

### 1. State Definition

**File: `src/agents/state.py`**

```python
"""
Shared state definition for multi-agent workflow
Uses LangGraph's TypedDict pattern for state management
"""

from typing import TypedDict, List, Dict, Optional, Annotated
from datetime import datetime
from langgraph.graph import add_messages
import operator


class AnalysisContext(TypedDict):
    """
    Shared context for contract analysis workflow

    This state is passed between all agents and accumulates results.
    Each agent reads from and writes to this shared context.
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

    findings: Annotated[List[Dict], operator.add]
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

    neutral_rationales: Annotated[List[Dict], operator.add]
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

    transformed_rationales: Annotated[List[Dict], operator.add]
    """
    Styled rationales from Personality Agent:
    {
        'transformation_id': str,
        'rationale_id': str,
        'style_params': {...},
        'transformed_text': str
    }
    """

    suggested_edits: Annotated[List[Dict], operator.add]
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
        style_params: Optional personality settings

    Returns:
        Initial AnalysisContext
    """
    now = datetime.utcnow().isoformat()

    # Default style params if not provided
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

        # Outputs (empty initially)
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
```

---

### 2. Agent Integration Pattern

Each agent follows this pattern for context management:

```python
from src.agents.state import AnalysisContext
from datetime import datetime

class ExampleAgent:
    """Example showing how agents interact with context"""

    async def process(self, state: AnalysisContext) -> AnalysisContext:
        """
        Process the context and return updated context

        Args:
            state: Current analysis context

        Returns:
            Updated context with this agent's outputs added
        """
        # Update metadata
        state['current_agent'] = self.__class__.__name__
        state['updated_at'] = datetime.utcnow().isoformat()

        try:
            # Read from context
            clauses = state['clauses']
            policies = state['policies']

            # Do work...
            results = self._do_analysis(clauses, policies)

            # Write to context (append to list)
            state['findings'].extend(results)

            # Update stage
            state['workflow_stage'] = 'next_stage'

        except Exception as e:
            # Log error to context
            state['errors'].append({
                'agent': self.__class__.__name__,
                'error_type': type(e).__name__,
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })

        return state
```

---

### 3. LangGraph Workflow Definition

**File: `src/agents/workflow.py`**

```python
"""
Multi-agent workflow orchestration using LangGraph
"""

from langgraph.graph import StateGraph, END
from src.agents.state import AnalysisContext
from src.agents.diligent_reviewer import DiligentReviewerAgent
from src.agents.neutral_rationale import NeutralRationaleAgent
from src.agents.personality import PersonalityAgent
from src.agents.editor import EditorAgent


def create_analysis_workflow() -> StateGraph:
    """
    Create the multi-agent analysis workflow graph

    Returns:
        Configured StateGraph ready to compile
    """

    # Initialize agents
    diligent_reviewer = DiligentReviewerAgent()
    neutral_rationale = NeutralRationaleAgent()
    personality = PersonalityAgent()
    editor = EditorAgent()

    # Create graph with typed state
    workflow = StateGraph(AnalysisContext)

    # Add nodes (agents)
    workflow.add_node("review", diligent_reviewer.process)
    workflow.add_node("rationale", neutral_rationale.process)
    workflow.add_node("personality", personality.process)
    workflow.add_node("edit", editor.process)

    # Define edges (workflow sequence)
    workflow.set_entry_point("review")
    workflow.add_edge("review", "rationale")
    workflow.add_edge("rationale", "personality")
    workflow.add_edge("personality", "edit")
    workflow.add_edge("edit", END)

    return workflow


# Compile workflow for use
analysis_workflow = create_analysis_workflow().compile()


async def analyze_contract(
    version_id: str,
    session_id: str,
    contract_text: str,
    clauses: List[Dict],
    policies: List[Dict],
    style_params: Optional[Dict] = None
) -> AnalysisContext:
    """
    Run complete contract analysis through multi-agent workflow

    Args:
        version_id: Document version UUID
        session_id: Negotiation session UUID
        contract_text: Full contract text
        clauses: Extracted clauses
        policies: Applicable policies
        style_params: Optional personality settings

    Returns:
        Final AnalysisContext with all agent outputs
    """
    from src.agents.state import create_initial_context

    # Create initial context
    initial_state = create_initial_context(
        version_id=version_id,
        session_id=session_id,
        contract_text=contract_text,
        clauses=clauses,
        policies=policies,
        style_params=style_params
    )

    # Run workflow
    final_state = await analysis_workflow.ainvoke(initial_state)

    # Mark complete
    final_state['workflow_stage'] = 'complete'

    return final_state
```

---

## Key Design Principles

### 1. **Immutability Where Possible**
- Input data (contract_text, clauses, policies) never changes
- Agents only append to lists, never modify existing items

### 2. **Progressive Enhancement**
- Context starts with minimal input
- Each agent adds its outputs
- Final context contains complete analysis

### 3. **Error Resilience**
- Errors logged to context, don't halt workflow
- Each agent can check for prior errors
- Workflow can implement retry logic

### 4. **Observability**
- `current_agent` shows progress
- `workflow_stage` enables monitoring
- `started_at`/`updated_at` for performance tracking

### 5. **Type Safety**
- TypedDict provides IDE autocomplete
- LangGraph validates state schema
- Easier debugging and maintenance

---

## Context Access Patterns

### Reading from Context

```python
# Agent reads previous agent's output
class NeutralRationaleAgent:
    async def process(self, state: AnalysisContext) -> AnalysisContext:
        # Read findings from Diligent Reviewer
        findings = state['findings']

        for finding in findings:
            # Generate rationale for this finding
            rationale = await self._generate_rationale(finding)

            # Append to context
            state['neutral_rationales'].append(rationale)

        return state
```

### Writing to Context

```python
# Agent adds its output to context
state['findings'].append({
    'finding_id': str(uuid4()),
    'clause_id': clause['clause_id'],
    'severity': 'high',
    'evidence_quote': "...",
    # ... more fields
})
```

### Checking for Errors

```python
# Agent checks if prior agents had errors
if state['errors']:
    # Log warning but continue
    logger.warning(f"Prior errors detected: {len(state['errors'])}")

# Or halt if critical errors
critical_errors = [e for e in state['errors'] if e['error_type'] == 'CriticalError']
if critical_errors:
    raise WorkflowHaltException("Critical errors in prior stages")
```

---

## Performance Considerations

### 1. **Context Size Management**
- Large contracts → large context
- Solution: Only include essential data in context
- Store full results in database, reference by ID

### 2. **Streaming Updates**
- LangGraph supports streaming state updates
- Can send progress updates to UI as agents work

### 3. **Checkpointing**
- LangGraph can checkpoint state between agents
- Enables resume after failures

---

## Testing Strategy

### Unit Tests

```python
def test_context_creation():
    """Test initial context creation"""
    context = create_initial_context(
        version_id="test-version",
        session_id="test-session",
        contract_text="Sample contract",
        clauses=[],
        policies=[]
    )

    assert context['version_id'] == "test-version"
    assert context['findings'] == []
    assert context['workflow_stage'] == 'reviewing'


def test_agent_adds_to_context():
    """Test agent modifies context correctly"""
    agent = DiligentReviewerAgent()
    context = create_initial_context(...)

    updated_context = await agent.process(context)

    assert len(updated_context['findings']) > 0
    assert updated_context['current_agent'] == 'DiligentReviewerAgent'
```

### Integration Tests

```python
async def test_full_workflow():
    """Test complete workflow with context"""
    result = await analyze_contract(
        version_id="test",
        session_id="test",
        contract_text="...",
        clauses=[...],
        policies=[...]
    )

    # Verify all agents ran
    assert len(result['findings']) > 0
    assert len(result['neutral_rationales']) > 0
    assert len(result['transformed_rationales']) > 0
    assert len(result['suggested_edits']) > 0
    assert result['workflow_stage'] == 'complete'
```

---

## Summary

**Context management is handled via:**

1. ✅ **LangGraph State** - Typed state object passed between agents
2. ✅ **Accumulation Pattern** - Each agent appends to lists
3. ✅ **Workflow Graph** - LangGraph orchestrates agent sequence
4. ✅ **Error Resilience** - Errors logged, workflow continues
5. ✅ **Type Safety** - TypedDict + validation

**Next steps:**
1. Implement `src/agents/state.py` (this design)
2. Implement `src/agents/workflow.py` (orchestration)
3. Update each agent to use `AnalysisContext`

This design ensures **clean handoffs** between agents with **full observability** and **type safety**! 🚀
