"""
Deep Agents Orchestration Layer

Implements advanced multi-agent coordination patterns:
1. Hierarchical Agent Teams (Manager + Specialist Agents)
2. Dynamic Agent Spawning (context-dependent agent creation)
3. Parallel Agent Pools (concurrent processing with load balancing)
4. Agent Memory & Learning (shared knowledge base)
5. Feedback Loops (iterative refinement)

Architecture:
- MetaOrchestrator: Top-level coordinator
- Team Leaders: Domain-specific coordinators
- Specialist Agents: Task-specific workers
- Knowledge Base: Shared learning repository
"""

import asyncio
import time
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from uuid import uuid4
import json

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from config.settings import settings
from src.agents.state import AnalysisContext, update_context_metadata
from src.agents.diligent_reviewer import DiligentReviewerAgent
from src.agents.neutral_rationale import NeutralRationaleAgent
from src.agents.personality import PersonalityAgent
from src.agents.editor import EditorAgent


# ============================================================================
# AGENT TEAMS
# ============================================================================

class AgentTeam:
    """
    Represents a coordinated team of agents working on a specific domain

    Pattern: Team Leader + Specialist Workers
    - Leader: Coordinates work, makes decisions, delegates tasks
    - Workers: Execute specific tasks assigned by leader
    """

    def __init__(self, team_name: str, leader_agent, worker_agents: List, max_concurrent: int = 5):
        self.team_name = team_name
        self.leader = leader_agent
        self.workers = worker_agents
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.metrics = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_time': 0,
            'average_time': 0
        }

    async def process(self, tasks: List[Dict], context: AnalysisContext) -> List[Dict]:
        """
        Process tasks through team coordination

        1. Leader analyzes tasks and creates execution plan
        2. Workers execute tasks in parallel
        3. Leader reviews and synthesizes results
        """
        start_time = time.time()

        # Step 1: Leader creates execution plan
        execution_plan = await self.leader.create_plan(tasks, context)

        # Step 2: Workers execute in parallel
        results = await self._execute_parallel(execution_plan['subtasks'])

        # Step 3: Leader synthesizes results
        final_result = await self.leader.synthesize(results, context)

        # Update metrics
        elapsed = time.time() - start_time
        self.metrics['tasks_completed'] += len(tasks)
        self.metrics['total_time'] += elapsed
        self.metrics['average_time'] = self.metrics['total_time'] / max(self.metrics['tasks_completed'], 1)

        return final_result

    async def _execute_parallel(self, subtasks: List[Dict]) -> List[Dict]:
        """Execute subtasks in parallel with load balancing"""

        async def execute_with_limit(subtask):
            async with self.semaphore:
                # Round-robin worker assignment
                worker_idx = subtask['id'] % len(self.workers)
                worker = self.workers[worker_idx]

                try:
                    result = await worker.execute(subtask)
                    return {'success': True, 'result': result}
                except Exception as e:
                    self.metrics['tasks_failed'] += 1
                    return {'success': False, 'error': str(e)}

        results = await asyncio.gather(*[execute_with_limit(st) for st in subtasks])
        return results


class TeamLeaderAgent:
    """
    Coordinates a team of specialist agents
    Responsibilities: Planning, delegation, synthesis
    """

    def __init__(self, domain: str):
        self.domain = domain
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            temperature=0.3,
            anthropic_api_key=settings.ANTHROPIC_API_KEY
        )

    async def create_plan(self, tasks: List[Dict], context: AnalysisContext) -> Dict:
        """Analyze tasks and create execution plan for workers"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a team leader coordinating {self.domain} analysis.

Analyze the tasks and create an execution plan:
1. Break down tasks into parallel-executable subtasks
2. Identify dependencies between subtasks
3. Estimate priority and complexity
4. Return JSON plan"""),
            ("user", f"Tasks: {json.dumps(tasks)}\n\nCreate execution plan:")
        ])

        response = await self.llm.ainvoke(prompt.format())

        # Parse plan
        content = response.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('\n```', 1)[0]

        plan = json.loads(content)
        return plan

    async def synthesize(self, results: List[Dict], context: AnalysisContext) -> Dict:
        """Combine worker results into final output"""

        # Filter successful results
        successful = [r['result'] for r in results if r.get('success')]

        return {
            'domain': self.domain,
            'results': successful,
            'success_rate': len(successful) / max(len(results), 1),
            'timestamp': datetime.utcnow().isoformat()
        }


# ============================================================================
# DYNAMIC AGENT SPAWNING
# ============================================================================

class AgentFactory:
    """
    Dynamically creates agents based on runtime context

    Pattern: Factory + Registry
    - Detects need for specialized agents during execution
    - Spawns new agent instances on-demand
    - Maintains agent pool for reuse
    """

    def __init__(self):
        self.agent_pool = {}  # Cache of created agents
        self.agent_registry = {
            'compliance_checker': DiligentReviewerAgent,
            'rationale_generator': NeutralRationaleAgent,
            'style_transformer': PersonalityAgent,
            'edit_generator': EditorAgent,
        }

    async def create_agent(self, agent_type: str, config: Optional[Dict] = None) -> Any:
        """Create or retrieve agent from pool"""

        cache_key = f"{agent_type}:{json.dumps(config or {})}"

        if cache_key in self.agent_pool:
            return self.agent_pool[cache_key]

        # Create new agent
        if agent_type in self.agent_registry:
            agent_class = self.agent_registry[agent_type]
            agent = agent_class()
            self.agent_pool[cache_key] = agent
            return agent

        raise ValueError(f"Unknown agent type: {agent_type}")

    def register_agent_type(self, name: str, agent_class):
        """Register new agent type dynamically"""
        self.agent_registry[name] = agent_class


# ============================================================================
# KNOWLEDGE BASE (SHARED LEARNING)
# ============================================================================

class AgentKnowledgeBase:
    """
    Shared knowledge repository for agent learning

    Pattern: Centralized Memory with Retrieval
    - Agents contribute learnings to shared base
    - Future agents retrieve relevant patterns
    - Improves efficiency over time
    """

    def __init__(self):
        self.patterns = {}  # clause_type -> common_issues
        self.success_strategies = {}  # issue_type -> resolution_strategies
        self.performance_stats = {}  # agent_type -> metrics

    async def learn_from_finding(self, finding: Dict):
        """Extract patterns from successful findings"""

        clause_type = finding.get('clause_type', 'unknown')
        issue_type = finding.get('issue_type', 'unknown')

        # Update pattern frequency
        if clause_type not in self.patterns:
            self.patterns[clause_type] = {}

        if issue_type not in self.patterns[clause_type]:
            self.patterns[clause_type][issue_type] = 0

        self.patterns[clause_type][issue_type] += 1

    async def get_recommendations(self, clause_type: str) -> List[str]:
        """Get recommended policies to check based on history"""

        if clause_type not in self.patterns:
            return []

        # Return most common issues sorted by frequency
        issues = self.patterns[clause_type]
        sorted_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)

        return [issue for issue, count in sorted_issues[:5]]

    async def update_performance(self, agent_type: str, metrics: Dict):
        """Track agent performance metrics"""

        if agent_type not in self.performance_stats:
            self.performance_stats[agent_type] = {
                'executions': 0,
                'total_time': 0,
                'success_count': 0
            }

        stats = self.performance_stats[agent_type]
        stats['executions'] += 1
        stats['total_time'] += metrics.get('time', 0)
        stats['success_count'] += 1 if metrics.get('success') else 0


# ============================================================================
# META ORCHESTRATOR (TOP LEVEL)
# ============================================================================

class DeepAgentOrchestrator:
    """
    Advanced multi-agent orchestrator with deep coordination

    Features:
    - Hierarchical teams (leaders + workers)
    - Dynamic agent spawning
    - Shared knowledge base
    - Adaptive execution strategies
    - Real-time performance optimization
    """

    def __init__(self):
        # Core components
        self.agent_factory = AgentFactory()
        self.knowledge_base = AgentKnowledgeBase()

        # Agent teams
        self.compliance_team = None
        self.analysis_team = None
        self.editing_team = None

        # Performance tracking
        self.execution_log = []

    async def initialize_teams(self):
        """Create agent teams dynamically"""

        # Compliance team: 1 leader + 3 worker reviewers
        compliance_leader = TeamLeaderAgent('compliance')
        compliance_workers = [
            await self.agent_factory.create_agent('compliance_checker')
            for _ in range(3)
        ]
        self.compliance_team = AgentTeam(
            'compliance',
            compliance_leader,
            compliance_workers,
            max_concurrent=10
        )

        # Analysis team: 1 leader + 2 rationale generators
        analysis_leader = TeamLeaderAgent('analysis')
        analysis_workers = [
            await self.agent_factory.create_agent('rationale_generator')
            for _ in range(2)
        ]
        self.analysis_team = AgentTeam(
            'analysis',
            analysis_leader,
            analysis_workers,
            max_concurrent=5
        )

        # Editing team: 1 leader + 2 editors
        editing_leader = TeamLeaderAgent('editing')
        editing_workers = [
            await self.agent_factory.create_agent('edit_generator')
            for _ in range(2)
        ]
        self.editing_team = AgentTeam(
            'editing',
            editing_leader,
            editing_workers,
            max_concurrent=5
        )

    async def analyze_contract_deep(self, state: AnalysisContext) -> AnalysisContext:
        """
        Deep orchestration workflow with adaptive strategies

        Workflow:
        1. Analyze complexity and create execution strategy
        2. Initialize teams dynamically based on workload
        3. Execute with parallel teams + knowledge base consultation
        4. Learn from results for future optimizations
        5. Synthesize and return
        """

        start_time = time.time()

        # Initialize teams if not already done
        if not self.compliance_team:
            await self.initialize_teams()

        # Step 1: Adaptive strategy selection
        strategy = await self._select_strategy(state)
        print(f"🧠 Selected strategy: {strategy['name']} (workload: {strategy['estimated_workload']} tasks)")

        # Step 2: Execute based on strategy
        if strategy['name'] == 'parallel_teams':
            state = await self._execute_parallel_teams(state)
        elif strategy['name'] == 'sequential_deep':
            state = await self._execute_sequential_deep(state)
        else:
            state = await self._execute_standard(state)

        # Step 3: Learn from execution
        await self._learn_from_execution(state)

        # Log performance
        elapsed = time.time() - start_time
        self.execution_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'strategy': strategy['name'],
            'clauses_processed': len(state['clauses']),
            'findings': len(state.get('findings', [])),
            'time': elapsed
        })

        print(f"✅ Deep orchestration complete in {elapsed:.1f}s")

        return state

    async def _select_strategy(self, state: AnalysisContext) -> Dict:
        """
        Intelligently select execution strategy based on context

        Factors:
        - Number of clauses
        - Complexity of policies
        - Historical performance
        - Available resources
        """

        num_clauses = len(state['clauses'])
        num_policies = len(state['policies'])
        estimated_workload = num_clauses * min(num_policies, 3)  # Max 3 policies per clause

        if estimated_workload > 50:
            return {
                'name': 'parallel_teams',
                'estimated_workload': estimated_workload,
                'reason': 'High workload requires parallel team execution'
            }
        elif estimated_workload > 20:
            return {
                'name': 'sequential_deep',
                'estimated_workload': estimated_workload,
                'reason': 'Medium workload with deep analysis'
            }
        else:
            return {
                'name': 'standard',
                'estimated_workload': estimated_workload,
                'reason': 'Low workload, standard pipeline sufficient'
            }

    async def _execute_parallel_teams(self, state: AnalysisContext) -> AnalysisContext:
        """Execute with multiple teams working in parallel"""

        # Compliance team processes all clauses
        diligent_reviewer = await self.agent_factory.create_agent('compliance_checker')
        state = await diligent_reviewer.process(state)

        # If findings, use analysis and editing teams in parallel
        if state.get('findings'):
            # Split findings between team instances for parallel processing
            rationale_agent = await self.agent_factory.create_agent('rationale_generator')
            personality_agent = await self.agent_factory.create_agent('style_transformer')
            editor_agent = await self.agent_factory.create_agent('edit_generator')

            # Process rationales, personality, and edits sequentially but efficiently
            state = await rationale_agent.process(state)
            state = await personality_agent.process(state)
            state = await editor_agent.process(state)

        return state

    async def _execute_sequential_deep(self, state: AnalysisContext) -> AnalysisContext:
        """Execute with knowledge base consultation"""

        # Use standard agents but with knowledge base augmentation
        diligent_reviewer = await self.agent_factory.create_agent('compliance_checker')

        # Consult knowledge base for clause-specific recommendations
        for clause in state['clauses']:
            recommendations = await self.knowledge_base.get_recommendations(
                clause.get('clause_type', 'unknown')
            )
            clause['kb_recommendations'] = recommendations

        state = await diligent_reviewer.process(state)

        # Continue with other agents
        if state.get('findings'):
            rationale_agent = await self.agent_factory.create_agent('rationale_generator')
            personality_agent = await self.agent_factory.create_agent('style_transformer')
            editor_agent = await self.agent_factory.create_agent('edit_generator')

            state = await rationale_agent.process(state)
            state = await personality_agent.process(state)
            state = await editor_agent.process(state)

        return state

    async def _execute_standard(self, state: AnalysisContext) -> AnalysisContext:
        """Standard sequential execution"""

        diligent_reviewer = await self.agent_factory.create_agent('compliance_checker')
        state = await diligent_reviewer.process(state)

        if state.get('findings'):
            rationale_agent = await self.agent_factory.create_agent('rationale_generator')
            personality_agent = await self.agent_factory.create_agent('style_transformer')
            editor_agent = await self.agent_factory.create_agent('edit_generator')

            state = await rationale_agent.process(state)
            state = await personality_agent.process(state)
            state = await editor_agent.process(state)

        return state

    async def _learn_from_execution(self, state: AnalysisContext):
        """Extract learnings from execution for future optimization"""

        # Learn patterns from findings
        for finding in state.get('findings', []):
            await self.knowledge_base.learn_from_finding(finding)

        # Update performance stats
        if self.execution_log:
            last_execution = self.execution_log[-1]
            await self.knowledge_base.update_performance(
                'deep_orchestrator',
                {
                    'time': last_execution['time'],
                    'success': True
                }
            )

    def get_performance_summary(self) -> Dict:
        """Get orchestrator performance summary"""

        if not self.execution_log:
            return {'executions': 0}

        total_time = sum(e['time'] for e in self.execution_log)
        total_clauses = sum(e['clauses_processed'] for e in self.execution_log)
        total_findings = sum(e['findings'] for e in self.execution_log)

        return {
            'total_executions': len(self.execution_log),
            'total_clauses_processed': total_clauses,
            'total_findings': total_findings,
            'average_time': total_time / len(self.execution_log),
            'average_findings_per_execution': total_findings / len(self.execution_log),
            'knowledge_base_patterns': len(self.knowledge_base.patterns),
            'team_metrics': {
                'compliance': self.compliance_team.metrics if self.compliance_team else {},
                'analysis': self.analysis_team.metrics if self.analysis_team else {},
                'editing': self.editing_team.metrics if self.editing_team else {}
            }
        }


# Convenience function for external use
async def analyze_with_deep_orchestration(
    version_id: str,
    session_id: str,
    contract_text: str,
    clauses: List[Dict],
    policies: List[Dict],
    style_params: Optional[Dict] = None
) -> Dict:
    """
    Analyze contract using deep agent orchestration

    Args:
        version_id: Document version ID
        session_id: Session ID
        contract_text: Full contract text
        clauses: Extracted clauses
        policies: Applicable policies
        style_params: Style configuration

    Returns:
        Analysis results with orchestrator metrics
    """

    from src.agents.state import create_initial_context

    # Create deep orchestrator
    orchestrator = DeepAgentOrchestrator()

    # Create initial state
    state = create_initial_context(
        version_id=version_id,
        session_id=session_id,
        contract_text=contract_text,
        clauses=clauses,
        policies=policies,
        style_params=style_params
    )

    # Execute deep orchestration
    final_state = await orchestrator.analyze_contract_deep(state)

    # Build result with orchestrator metrics
    result = {
        'version_id': version_id,
        'session_id': session_id,
        'findings': final_state.get('findings', []),
        'neutral_rationales': final_state.get('neutral_rationales', []),
        'transformed_rationales': final_state.get('transformed_rationales', []),
        'suggested_edits': final_state.get('suggested_edits', []),
        'orchestration_metrics': orchestrator.get_performance_summary(),
        'metadata': {
            'clauses_analyzed': len(clauses),
            'policies_applied': len(policies),
            'workflow_stage': final_state.get('workflow_stage')
        }
    }

    return result
