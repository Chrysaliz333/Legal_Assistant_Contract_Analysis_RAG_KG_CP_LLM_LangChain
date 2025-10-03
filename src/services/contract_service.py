"""
Contract Service for Version Management
REQ-VC-001: Version creation with UUID + timestamp + hash
REQ-VC-005: Rollback capability
REQ-VC-007: RBAC permissions
"""

from typing import Optional, List, Dict
from uuid import uuid4
import hashlib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from src.models.sessions import NegotiationSession, DocumentVersion
from src.models.clauses import Clause
from src.models.audit import NegotiationLog


class ContractService:
    """
    Service for contract version management
    Handles CRUD operations for contracts, versions, and clauses
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        organization_id: str,
        contract_name: str,
        counterparty_id: Optional[str] = None,
        matter_id: Optional[str] = None,
        style_overrides: Optional[Dict] = None
    ) -> NegotiationSession:
        """
        Create new negotiation session

        Args:
            organization_id: UUID of organization
            contract_name: Name of contract
            counterparty_id: Optional counterparty UUID
            matter_id: Optional external matter ID
            style_overrides: Optional personality settings for this session

        Returns:
            Created NegotiationSession
        """
        session = NegotiationSession(
            session_id=uuid4(),
            organization_id=organization_id,
            contract_name=contract_name,
            counterparty_id=counterparty_id,
            matter_id=matter_id,
            status='active',
            style_overrides=style_overrides
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def create_version(
        self,
        session_id: str,
        file_path: str,
        file_name: str,
        document_hash: str,
        source: str = 'internal',
        uploader_id: Optional[str] = None,
        parent_version_id: Optional[str] = None,
        clauses: Optional[List[Dict]] = None
    ) -> DocumentVersion:
        """
        Create new document version
        REQ-VC-001: Version creation with UUID, timestamp, hash

        Args:
            session_id: UUID of negotiation session
            file_path: Path to stored document
            file_name: Original filename
            document_hash: SHA-256 hash of document
            source: 'internal' or 'counterparty'
            uploader_id: UUID of user who uploaded
            parent_version_id: UUID of parent version (for tracking changes)
            clauses: Optional list of extracted clauses to create

        Returns:
            Created DocumentVersion with clauses
        """
        # Get session to determine version number
        stmt = select(NegotiationSession).where(
            NegotiationSession.session_id == session_id
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one()

        # Get current max version number for this session
        stmt = select(DocumentVersion).where(
            DocumentVersion.session_id == session_id
        ).order_by(desc(DocumentVersion.version_number))
        result = await self.db.execute(stmt)
        latest_version = result.scalar_one_or_none()

        version_number = (latest_version.version_number + 1) if latest_version else 1

        # Create version
        version = DocumentVersion(
            version_id=uuid4(),
            session_id=session_id,
            parent_version_id=parent_version_id,
            version_number=version_number,
            source=source,
            document_hash=document_hash,
            file_path=file_path,
            file_name=file_name,
            uploader_id=uploader_id
        )

        self.db.add(version)
        await self.db.flush()  # Get version_id before adding clauses

        # Create clauses if provided
        if clauses:
            for clause_data in clauses:
                clause = Clause(
                    clause_id=uuid4(),
                    version_id=version.version_id,
                    clause_identifier=clause_data.get('clause_identifier'),
                    clause_type=clause_data.get('clause_type'),
                    clause_text=clause_data['clause_text'],
                    char_start=clause_data.get('char_start'),
                    char_end=clause_data.get('char_end'),
                    xpath=clause_data.get('xpath'),
                    paragraph_id=clause_data.get('paragraph_id')
                )
                self.db.add(clause)

        # Log version creation
        log_entry = NegotiationLog(
            log_entry_id=uuid4(),
            session_id=session_id,
            version_id=version.version_id,
            change_type='version_creation',
            after_state={'version_number': version_number, 'source': source},
            source=source,
            actor_id=uploader_id
        )
        self.db.add(log_entry)

        await self.db.commit()
        await self.db.refresh(version)

        return version

    async def get_version(
        self,
        version_id: str,
        include_clauses: bool = True
    ) -> Optional[DocumentVersion]:
        """
        Retrieve document version by ID

        Args:
            version_id: UUID of version
            include_clauses: Whether to load clauses

        Returns:
            DocumentVersion or None if not found
        """
        stmt = select(DocumentVersion).where(
            DocumentVersion.version_id == version_id
        )

        if include_clauses:
            stmt = stmt.options(selectinload(DocumentVersion.clauses))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_versions(
        self,
        session_id: str,
        include_clauses: bool = False
    ) -> List[DocumentVersion]:
        """
        Get all versions for a session

        Args:
            session_id: UUID of negotiation session
            include_clauses: Whether to load clauses for each version

        Returns:
            List of DocumentVersions ordered by version_number
        """
        stmt = select(DocumentVersion).where(
            DocumentVersion.session_id == session_id
        ).order_by(DocumentVersion.version_number)

        if include_clauses:
            stmt = stmt.options(selectinload(DocumentVersion.clauses))

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_current_version(
        self,
        session_id: str,
        include_clauses: bool = True
    ) -> Optional[DocumentVersion]:
        """
        Get the current (latest) version for a session

        Args:
            session_id: UUID of negotiation session
            include_clauses: Whether to load clauses

        Returns:
            Latest DocumentVersion or None
        """
        stmt = select(DocumentVersion).where(
            DocumentVersion.session_id == session_id
        ).order_by(desc(DocumentVersion.version_number)).limit(1)

        if include_clauses:
            stmt = stmt.options(selectinload(DocumentVersion.clauses))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def rollback_to_version(
        self,
        session_id: str,
        target_version_id: str,
        reason: str,
        actor_id: str
    ) -> DocumentVersion:
        """
        Create new version by rolling back to a previous version
        REQ-VC-005: Non-destructive rollback

        Args:
            session_id: UUID of negotiation session
            target_version_id: UUID of version to rollback to
            reason: Reason for rollback
            actor_id: UUID of user performing rollback

        Returns:
            New DocumentVersion (copy of target version)
        """
        # Get target version
        target = await self.get_version(target_version_id, include_clauses=True)
        if not target:
            raise ValueError(f"Version {target_version_id} not found")

        if target.session_id != session_id:
            raise ValueError("Version does not belong to this session")

        # Create new version as copy of target
        new_version = await self.create_version(
            session_id=session_id,
            file_path=target.file_path,
            file_name=target.file_name,
            document_hash=target.document_hash,
            source='internal',
            uploader_id=actor_id,
            parent_version_id=target.version_id,
            clauses=[
                {
                    'clause_identifier': c.clause_identifier,
                    'clause_type': c.clause_type,
                    'clause_text': c.clause_text,
                    'char_start': c.char_start,
                    'char_end': c.char_end,
                    'xpath': c.xpath,
                    'paragraph_id': c.paragraph_id
                }
                for c in target.clauses
            ]
        )

        # Update rollback fields
        new_version.rollback_to = target_version_id
        new_version.rollback_reason = reason

        # Log rollback
        log_entry = NegotiationLog(
            log_entry_id=uuid4(),
            session_id=session_id,
            version_id=new_version.version_id,
            change_type='rollback',
            before_state={'current_version': None},
            after_state={
                'rolled_back_to': str(target_version_id),
                'target_version_number': target.version_number,
                'reason': reason
            },
            source='internal',
            actor_id=actor_id
        )
        self.db.add(log_entry)

        await self.db.commit()
        await self.db.refresh(new_version)

        return new_version

    async def get_version_lineage(
        self,
        version_id: str
    ) -> List[DocumentVersion]:
        """
        Get complete lineage (ancestry) of a version

        Args:
            version_id: UUID of version

        Returns:
            List of DocumentVersions from root to specified version
        """
        lineage = []
        current_id = version_id

        while current_id:
            version = await self.get_version(current_id, include_clauses=False)
            if not version:
                break

            lineage.insert(0, version)  # Add to front
            current_id = version.parent_version_id

        return lineage

    def calculate_document_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of document content
        REQ-VC-001: Document hash for integrity verification

        Args:
            content: Document content as bytes

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(content).hexdigest()

    async def get_negotiation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[NegotiationLog]:
        """
        Get negotiation history for a session
        REQ-VC-004: Audit trail retrieval

        Args:
            session_id: UUID of negotiation session
            limit: Optional limit on number of entries

        Returns:
            List of NegotiationLog entries ordered by timestamp
        """
        stmt = select(NegotiationLog).where(
            NegotiationLog.session_id == session_id
        ).order_by(desc(NegotiationLog.timestamp))

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def check_user_permission(
        self,
        user_id: str,
        action: str
    ) -> bool:
        """
        Check if user has permission for action
        REQ-VC-007: RBAC permission checking

        Args:
            user_id: UUID of user
            action: Action to check ('read', 'comment', 'edit', 'approve', 'rollback')

        Returns:
            True if user has permission
        """
        from src.models.users import User

        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return False

        return user.has_permission(action)
