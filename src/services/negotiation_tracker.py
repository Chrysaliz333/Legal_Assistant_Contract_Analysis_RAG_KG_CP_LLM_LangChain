"""
Negotiation Tracker Service
Tracks multiple versions of the same contract and compares changes
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import difflib
from dataclasses import dataclass, asdict


@dataclass
class ContractVersion:
    """Represents a single version of a contract"""
    version_id: str
    negotiation_id: str
    version_number: int
    contract_text: str
    uploaded_at: str
    uploaded_by: str  # 'internal' or 'counterparty'
    file_hash: str
    analysis_result: Optional[Dict] = None
    notes: Optional[str] = None


class NegotiationTracker:
    """
    Tracks contract versions across negotiation rounds

    Features:
    - Store multiple versions of same contract
    - Compare any two versions (text diff)
    - Track what changed between rounds
    - Identify accepted/rejected changes
    - Timeline view of negotiation
    """

    def __init__(self, storage_dir: str = "negotiations"):
        """
        Initialize negotiation tracker

        Args:
            storage_dir: Directory to store negotiation data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def create_negotiation(self, negotiation_id: str, title: str) -> Dict:
        """
        Create a new negotiation tracking record

        Args:
            negotiation_id: Unique ID for this negotiation
            title: Human-readable title (e.g., "Acme Corp SaaS Agreement")

        Returns:
            Negotiation metadata
        """
        negotiation = {
            'negotiation_id': negotiation_id,
            'title': title,
            'created_at': datetime.utcnow().isoformat(),
            'versions': [],
            'status': 'active'  # active, completed, abandoned
        }

        self._save_negotiation(negotiation)
        return negotiation

    def add_version(
        self,
        negotiation_id: str,
        contract_text: str,
        uploaded_by: str = 'internal',
        notes: Optional[str] = None,
        analysis_result: Optional[Dict] = None
    ) -> ContractVersion:
        """
        Add a new version to an existing negotiation

        Args:
            negotiation_id: ID of the negotiation
            contract_text: Full contract text
            uploaded_by: 'internal' or 'counterparty'
            notes: Optional notes about this version
            analysis_result: Optional analysis from unified agent

        Returns:
            ContractVersion object
        """
        # Load existing negotiation
        negotiation = self._load_negotiation(negotiation_id)

        # Calculate version number
        version_number = len(negotiation['versions']) + 1

        # Generate version ID and hash
        version_id = f"{negotiation_id}_v{version_number}"
        file_hash = hashlib.sha256(contract_text.encode()).hexdigest()[:16]

        # Check for duplicate (same hash)
        for existing_version in negotiation['versions']:
            if existing_version.get('file_hash') == file_hash:
                raise ValueError(f"Duplicate version detected (identical to version {existing_version['version_number']})")

        # Create version object
        version = ContractVersion(
            version_id=version_id,
            negotiation_id=negotiation_id,
            version_number=version_number,
            contract_text=contract_text,
            uploaded_at=datetime.utcnow().isoformat(),
            uploaded_by=uploaded_by,
            file_hash=file_hash,
            analysis_result=analysis_result,
            notes=notes
        )

        # Save version
        self._save_version(version)

        # Update negotiation
        negotiation['versions'].append({
            'version_id': version_id,
            'version_number': version_number,
            'uploaded_at': version.uploaded_at,
            'uploaded_by': uploaded_by,
            'file_hash': file_hash,
            'notes': notes
        })

        self._save_negotiation(negotiation)

        return version

    def get_version(self, version_id: str) -> ContractVersion:
        """Load a specific version"""
        version_path = self.storage_dir / f"{version_id}.json"

        if not version_path.exists():
            raise ValueError(f"Version {version_id} not found")

        with open(version_path, 'r') as f:
            data = json.load(f)

        return ContractVersion(**data)

    def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str
    ) -> Dict:
        """
        Compare two versions and return structured diff

        Args:
            version_id_1: Older version (base)
            version_id_2: Newer version (compare)

        Returns:
            Dict with comparison results
        """
        v1 = self.get_version(version_id_1)
        v2 = self.get_version(version_id_2)

        # Generate unified diff
        diff = list(difflib.unified_diff(
            v1.contract_text.splitlines(keepends=True),
            v2.contract_text.splitlines(keepends=True),
            fromfile=f"Version {v1.version_number}",
            tofile=f"Version {v2.version_number}",
            lineterm=''
        ))

        # Count changes
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        # Extract changed sections
        changes = []
        current_change = {'type': None, 'lines': []}

        for line in diff:
            if line.startswith('+++') or line.startswith('---'):
                continue
            elif line.startswith('@@'):
                if current_change['lines']:
                    changes.append(current_change)
                current_change = {'type': 'context', 'lines': [line]}
            elif line.startswith('+'):
                current_change['type'] = 'addition'
                current_change['lines'].append(line[1:])
            elif line.startswith('-'):
                current_change['type'] = 'deletion'
                current_change['lines'].append(line[1:])
            else:
                current_change['lines'].append(line)

        if current_change['lines']:
            changes.append(current_change)

        return {
            'version_1': {
                'version_id': v1.version_id,
                'version_number': v1.version_number,
                'uploaded_at': v1.uploaded_at,
                'uploaded_by': v1.uploaded_by
            },
            'version_2': {
                'version_id': v2.version_id,
                'version_number': v2.version_number,
                'uploaded_at': v2.uploaded_at,
                'uploaded_by': v2.uploaded_by
            },
            'summary': {
                'additions': additions,
                'deletions': deletions,
                'total_changes': additions + deletions
            },
            'diff_unified': ''.join(diff),
            'changes': changes
        }

    def get_negotiation_timeline(self, negotiation_id: str) -> List[Dict]:
        """
        Get chronological timeline of all versions

        Returns:
            List of version summaries in chronological order
        """
        negotiation = self._load_negotiation(negotiation_id)

        timeline = []
        for version_meta in negotiation['versions']:
            version = self.get_version(version_meta['version_id'])

            # Summarize analysis results
            analysis_summary = None
            if version.analysis_result:
                findings = version.analysis_result.get('findings', [])
                analysis_summary = {
                    'total_findings': len(findings),
                    'critical': sum(1 for f in findings if f.get('severity') == 'critical'),
                    'high': sum(1 for f in findings if f.get('severity') == 'high'),
                    'suggested_edits': sum(1 for f in findings if f.get('suggested_edit'))
                }

            timeline.append({
                'version_number': version.version_number,
                'version_id': version.version_id,
                'uploaded_at': version.uploaded_at,
                'uploaded_by': version.uploaded_by,
                'notes': version.notes,
                'analysis_summary': analysis_summary
            })

        return timeline

    def list_negotiations(self) -> List[Dict]:
        """List all negotiations"""
        negotiations = []

        for file in self.storage_dir.glob("*_negotiation.json"):
            with open(file, 'r') as f:
                neg = json.load(f)
                negotiations.append({
                    'negotiation_id': neg['negotiation_id'],
                    'title': neg['title'],
                    'created_at': neg['created_at'],
                    'version_count': len(neg['versions']),
                    'status': neg['status']
                })

        return sorted(negotiations, key=lambda x: x['created_at'], reverse=True)

    # Private helper methods

    def _save_negotiation(self, negotiation: Dict):
        """Save negotiation metadata"""
        path = self.storage_dir / f"{negotiation['negotiation_id']}_negotiation.json"
        with open(path, 'w') as f:
            json.dump(negotiation, f, indent=2)

    def _load_negotiation(self, negotiation_id: str) -> Dict:
        """Load negotiation metadata"""
        path = self.storage_dir / f"{negotiation_id}_negotiation.json"

        if not path.exists():
            # Auto-create if doesn't exist
            return self.create_negotiation(negotiation_id, f"Negotiation {negotiation_id}")

        with open(path, 'r') as f:
            return json.load(f)

    def _save_version(self, version: ContractVersion):
        """Save version data"""
        path = self.storage_dir / f"{version.version_id}.json"
        with open(path, 'w') as f:
            json.dump(asdict(version), f, indent=2)
