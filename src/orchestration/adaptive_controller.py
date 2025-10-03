"""Adaptive orchestration layer for contract-review agents."""

from __future__ import annotations

import asyncio
import difflib
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.agents.state import AnalysisContext, create_initial_context
from src.orchestration.project_memory import ProjectMemory
from src.orchestration.task_manager import Task, TaskManager

try:
    from src.agents.diligent_reviewer import DiligentReviewerAgent
    from src.agents.neutral_rationale import NeutralRationaleAgent
    from src.agents.personality import PersonalityAgent
    from src.agents.editor import EditorAgent
except Exception:  # pragma: no cover - optional dependency during tests
    DiligentReviewerAgent = None  # type: ignore
    NeutralRationaleAgent = None  # type: ignore
    PersonalityAgent = None  # type: ignore
    EditorAgent = None  # type: ignore


@dataclass
class AgentTaskResult:
    """Outcome produced by an agent after handling a task."""

    status: str
    notes: Optional[str] = None
    new_tasks: Sequence[Dict[str, Any]] = field(default_factory=list)


class AgentAdapter:
    """Adapter around existing workflow agents with task routing metadata."""

    def __init__(
        self,
        name: str,
        supported_tasks: Iterable[str],
        process_fn,
    ) -> None:
        self.name = name
        self._supported = set(supported_tasks)
        self._process = process_fn

    def supports(self, task_type: str) -> bool:
        return task_type in self._supported

    async def handle(self, context: AnalysisContext) -> AnalysisContext:
        return await self._process(context)


class AdaptiveOrchestrator:
    """Coordinates agents using shared project memory and dynamic task queues."""

    def __init__(
        self,
        project_memory: Optional[ProjectMemory] = None,
        task_manager: Optional[TaskManager] = None,
        agents: Optional[Sequence[AgentAdapter]] = None,
    ) -> None:
        self.memory = project_memory or ProjectMemory()
        self.tasks = task_manager or TaskManager()
        self.agents = list(agents or self._build_default_agents())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ingest_contract(
        self,
        project_id: str,
        session_id: str,
        version_id: str,
        contract_text: str,
        clauses: List[Dict[str, Any]],
        policies: List[Dict[str, Any]],
        notes: Optional[str] = None,
        graph_snapshot: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        style_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Register a new contract version and seed initial tasks."""

        checksum = hashlib.sha256(contract_text.encode("utf-8")).hexdigest()
        diff_summary = self._generate_diff(project_id, contract_text)
        self.memory.record_version(
            project_id=project_id,
            version_id=version_id,
            source="upload",
            checksum=checksum,
            notes=notes,
            graph_snapshot=graph_snapshot,
            diff_summary=diff_summary,
            contract_text=contract_text,
        )

        if preferences:
            for key, value in preferences.items():
                self.memory.record_preference(
                    project_id=project_id,
                    user_id=session_id,
                    key=key,
                    value=value,
                    source="session",
                )

        context_id = f"{project_id}:{version_id}"
        context = create_initial_context(
            version_id=version_id,
            session_id=session_id,
            contract_text=contract_text,
            clauses=clauses,
            policies=policies,
            style_params=style_params,
        )
        self.memory.store_context(context_id, context)

        # Bootstrap review task
        self.tasks.enqueue(
            task_type="clause_review",
            payload={
                "context_id": context_id,
                "project_id": project_id,
                "version_id": version_id,
                "session_id": session_id,
            },
            priority=1,
        )

        self.memory.log_agent_event(
            project_id=project_id,
            version_id=version_id,
            agent_name="orchestrator",
            action="ingest_version",
            payload={"context_id": context_id, "diff_summary": diff_summary},
        )

        return context_id

    async def run(self, max_iterations: int = 25) -> None:
        """Process queued tasks until exhausted or iteration limit reached."""

        iterations = 0
        while iterations < max_iterations:
            task = self.tasks.dequeue()
            if not task:
                break

            agent = self._select_agent(task.task_type)
            if not agent:
                self.tasks.mark_complete(task.task_id, {"error": "no_agent"})
                iterations += 1
                continue

            context = self._load_context(task)
            if context is None:
                self.tasks.mark_complete(task.task_id, {"error": "missing_context"})
                iterations += 1
                continue

            try:
                updated_context = await agent.handle(context)
                self.memory.store_context(task.payload["context_id"], updated_context)
                result = self._post_process(agent.name, task, updated_context)
                self.memory.log_agent_event(
                    project_id=task.payload["project_id"],
                    version_id=task.payload["version_id"],
                    agent_name=agent.name,
                    action="completed",
                    payload={"task_type": task.task_type, "notes": result.notes},
                )
                for spec in result.new_tasks:
                    payload = dict(spec.get("payload", {}))
                    payload.setdefault("context_id", task.payload["context_id"])
                    payload.setdefault("project_id", task.payload["project_id"])
                    payload.setdefault("version_id", task.payload["version_id"])
                    payload.setdefault("session_id", task.payload["session_id"])
                    self.tasks.enqueue(
                        task_type=spec["task_type"],
                        payload=payload,
                        priority=spec.get("priority", task.priority + 1),
                        depends_on=spec.get("depends_on"),
                    )
                self.tasks.mark_complete(task.task_id, {"status": result.status})
            except Exception as exc:  # pragma: no cover - defensive logging
                self.memory.log_agent_event(
                    project_id=task.payload["project_id"],
                    version_id=task.payload["version_id"],
                    agent_name=agent.name,
                    action="error",
                    payload={"task_type": task.task_type, "error": str(exc)},
                )
                self.tasks.mark_complete(task.task_id, {"error": str(exc)})
            iterations += 1

    def get_context(self, context_id: str) -> Optional[AnalysisContext]:
        stored = self.memory.get_context(context_id)
        return stored  # type: ignore[return-value]

    def build_result(self, context_id: str) -> Optional[Dict[str, Any]]:
        context = self.get_context(context_id)
        if context is None:
            return None
        summary = self._build_summary(context)
        return {
            "version_id": context.get("version_id"),
            "session_id": context.get("session_id"),
            "workflow_stage": context.get("workflow_stage"),
            "analysis_summary": summary,
            "findings": context.get("findings", []),
            "neutral_rationales": context.get("neutral_rationales", []),
            "transformed_rationales": context.get("transformed_rationales", []),
            "suggested_edits": context.get("suggested_edits", []),
            "errors": context.get("errors", []),
            "metadata": {
                "started_at": context.get("started_at"),
                "completed_at": context.get("updated_at"),
                "current_agent": context.get("current_agent"),
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _select_agent(self, task_type: str) -> Optional[AgentAdapter]:
        for agent in self.agents:
            if agent.supports(task_type):
                return agent
        return None

    def _load_context(self, task: Task) -> Optional[AnalysisContext]:
        stored = self.memory.get_context(task.payload["context_id"])
        return stored  # type: ignore[return-value]

    def _post_process(
        self,
        agent_name: str,
        task: Task,
        context: AnalysisContext,
    ) -> AgentTaskResult:
        """Determine follow-on tasks based on the completed work."""

        transitions = {
            "clause_review": ["neutral_rationale"],
            "neutral_rationale": ["style_pass"],
            "style_pass": ["editor_pass"],
        }
        next_tasks = []
        for next_type in transitions.get(task.task_type, []):
            next_tasks.append({
                "task_type": next_type,
                "priority": task.priority + 1,
                "depends_on": task.task_id,
            })
        status = "complete" if next_tasks else "terminal"
        notes = f"{agent_name} handled {task.task_type}"
        return AgentTaskResult(status=status, notes=notes, new_tasks=next_tasks)

    def _generate_diff(self, project_id: str, new_text: str) -> Optional[str]:
        prev_contract = self.memory.get_latest_contract_text(project_id)
        if not prev_contract:
            return None
        diff_lines = difflib.unified_diff(
            prev_contract.splitlines(),
            new_text.splitlines(),
            lineterm="",
        )
        snippet = "\n".join(list(diff_lines)[:20])
        return snippet or None

    def _build_summary(self, context: AnalysisContext) -> Dict[str, Any]:
        findings = context.get("findings", [])
        rationales = context.get("neutral_rationales", [])
        edits = context.get("suggested_edits", [])

        severity_counts: Dict[str, int] = {}
        for finding in findings:
            severity = str(finding.get("severity", "unknown")).lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        conflict_count = sum(
            1 for edit in edits if edit.get("conflicts_with")
        )

        return {
            "total_findings": len(findings),
            "total_rationales": len(rationales),
            "total_edits": len(edits),
            "by_severity": severity_counts,
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0),
            "edits_with_conflicts": conflict_count,
            "style_params": context.get("style_params", {}),
            "has_errors": len(context.get("errors", [])) > 0,
        }

    def _build_default_agents(self) -> List[AgentAdapter]:
        """Create adapters for the existing four agents when available."""

        adapters: List[AgentAdapter] = []
        if DiligentReviewerAgent:
            reviewer = DiligentReviewerAgent()
            adapters.append(
                AgentAdapter(
                    name="DiligentReviewer",
                    supported_tasks=["clause_review"],
                    process_fn=reviewer.process,
                )
            )
        if NeutralRationaleAgent:
            rationale = NeutralRationaleAgent()
            adapters.append(
                AgentAdapter(
                    name="NeutralRationale",
                    supported_tasks=["neutral_rationale"],
                    process_fn=rationale.process,
                )
            )
        if PersonalityAgent:
            personality = PersonalityAgent()
            adapters.append(
                AgentAdapter(
                    name="Personality",
                    supported_tasks=["style_pass"],
                    process_fn=personality.process,
                )
            )
        if EditorAgent:
            editor = EditorAgent()
            adapters.append(
                AgentAdapter(
                    name="Editor",
                    supported_tasks=["editor_pass"],
                    process_fn=editor.process,
                )
            )
        return adapters

    # Convenience for synchronous contexts
    def run_sync(self, max_iterations: int = 25) -> None:
        asyncio.run(self.run(max_iterations=max_iterations))
