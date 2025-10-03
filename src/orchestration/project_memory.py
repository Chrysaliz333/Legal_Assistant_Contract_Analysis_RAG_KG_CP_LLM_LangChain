"""Project-level memory for negotiation history and preferences."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class VersionRecord:
    """Metadata describing a single contract version."""

    version_id: str
    source: str
    checksum: str
    created_at: str
    notes: Optional[str] = None
    diff_summary: Optional[str] = None
    graph_snapshot: Optional[str] = None


@dataclass
class PreferenceRecord:
    """Captured user preference with optional rationale."""

    key: str
    value: Any
    rationale: Optional[str]
    updated_at: str
    source: str


@dataclass
class AgentEvent:
    """Audit trail entry for agent activity."""

    timestamp: str
    agent: str
    action: str
    version_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


class ProjectMemory:
    """Persist negotiation history, preferences, and agent logs per project."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = base_path or Path("project_memory")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._live_contexts: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------
    def record_version(
        self,
        project_id: str,
        version_id: str,
        source: str,
        checksum: str,
        notes: Optional[str] = None,
        graph_snapshot: Optional[str] = None,
        diff_summary: Optional[str] = None,
        contract_text: Optional[str] = None,
    ) -> None:
        """Append a version record to the project timeline."""

        project = self._load_project(project_id)
        record = VersionRecord(
            version_id=version_id,
            source=source,
            checksum=checksum,
            created_at=datetime.utcnow().isoformat(),
            notes=notes,
            diff_summary=diff_summary,
            graph_snapshot=graph_snapshot,
        )
        project.setdefault("versions", []).append(record.__dict__)
        if contract_text is not None:
            project["latest_contract_text"] = contract_text
        self._save_project(project_id, project)

    def get_version_history(self, project_id: str) -> List[Dict[str, Any]]:
        project = self._load_project(project_id)
        return project.get("versions", [])

    # ------------------------------------------------------------------
    # Preference handling
    # ------------------------------------------------------------------
    def record_preference(
        self,
        project_id: str,
        user_id: str,
        key: str,
        value: Any,
        rationale: Optional[str] = None,
        source: str = "user",
    ) -> None:
        """Persist a preference value for a given user within the project."""

        project = self._load_project(project_id)
        user_prefs = project.setdefault("preferences", {}).setdefault(user_id, {})
        pref = PreferenceRecord(
            key=key,
            value=value,
            rationale=rationale,
            updated_at=datetime.utcnow().isoformat(),
            source=source,
        )
        user_prefs[key] = pref.__dict__
        self._save_project(project_id, project)

    def get_preferences(self, project_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
        project = self._load_project(project_id)
        return project.get("preferences", {}).get(user_id, {})

    # ------------------------------------------------------------------
    # Agent event logging
    # ------------------------------------------------------------------
    def log_agent_event(
        self,
        project_id: str,
        version_id: str,
        agent_name: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an agent event for auditability."""

        project = self._load_project(project_id)
        events = project.setdefault("agent_events", [])
        event = AgentEvent(
            timestamp=datetime.utcnow().isoformat(),
            agent=agent_name,
            action=action,
            version_id=version_id,
            payload=payload or {},
        )
        events.append(event.__dict__)
        self._save_project(project_id, project)

    def get_agent_events(self, project_id: str) -> List[Dict[str, Any]]:
        project = self._load_project(project_id)
        return project.get("agent_events", [])

    def get_latest_contract_text(self, project_id: str) -> Optional[str]:
        project = self._load_project(project_id)
        return project.get("latest_contract_text")

    # ------------------------------------------------------------------
    # Context management (non-persistent session state)
    # ------------------------------------------------------------------
    def store_context(self, context_id: str, context: Dict[str, Any]) -> None:
        """Store workflow context in memory for ongoing tasks."""
        self._live_contexts[context_id] = context

    def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored context by id."""
        return self._live_contexts.get(context_id)

    def discard_context(self, context_id: str) -> None:
        self._live_contexts.pop(context_id, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _project_file(self, project_id: str) -> Path:
        return self.base_path / f"{project_id}.json"

    def _load_project(self, project_id: str) -> Dict[str, Any]:
        file_path = self._project_file(project_id)
        if not file_path.exists():
            return {"project_id": project_id, "versions": [], "preferences": {}, "agent_events": []}
        try:
            return json.loads(file_path.read_text())
        except json.JSONDecodeError:
            return {"project_id": project_id, "versions": [], "preferences": {}, "agent_events": []}

    def _save_project(self, project_id: str, data: Dict[str, Any]) -> None:
        file_path = self._project_file(project_id)
        file_path.write_text(json.dumps(data, indent=2, sort_keys=True))
