"""
Diligent Reviewer Agent
REQ-DR-001: Policy Checking with Severity Labels
REQ-DR-002: Auto-Detection of Compliance
REQ-DR-003: Evidence Anchoring for High-Risk Findings
REQ-DR-004: Structured Findings Output
REQ-DR-005: Traceability with Provenance Logging
"""

from typing import List, Dict, Optional
from uuid import uuid4
from datetime import datetime
import json
import asyncio
import time

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from config.settings import settings
from src.agents.state import AnalysisContext, update_context_metadata, log_error_to_context
from src.services.embedding_service import embedding_service


class DiligentReviewerAgent:
    """
    Diligent Reviewer Agent - First stage of analysis

    Responsibilities:
    - Review each clause against applicable policies
    - Flag deviations with severity classification
    - Provide evidence quotes for high-risk findings
    - Generate structured findings with complete provenance
    """

    def __init__(self):
        # Use Haiku for fast, cheap policy checking (75% faster than Sonnet)
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-20241022",  # Fast model for simple compliance checks
            max_tokens=512,  # Simple JSON responses
            temperature=0.1,  # Low temperature for consistent policy checking
            timeout=settings.CLAUDE_TIMEOUT,
            anthropic_api_key=settings.ANTHROPIC_API_KEY
        )

    async def process(self, state: AnalysisContext) -> AnalysisContext:
        """
        Main entry point for agent processing
        Uses parallel LLM calls with bounded concurrency for performance

        Args:
            state: Current analysis context

        Returns:
            Updated context with findings added
        """
        # Update metadata
        state = update_context_metadata(state, "DiligentReviewerAgent", "reviewing")

        try:
            # Get data from context
            clauses = state['clauses']
            policies = state['policies']
            version_id = state['version_id']

            # Pre-generate unique clause-policy pairs to check
            pairs_to_check = []
            checked_pairs = set()

            for clause in clauses:
                # Find relevant policies for this clause
                relevant_policies = await self._get_relevant_policies(
                    clause,
                    policies
                )

                for policy in relevant_policies:
                    clause_id = clause.get('clause_id')
                    policy_id = policy.get('policy_id')

                    # Skip if we've already queued this pair
                    pair_key = f"{clause_id}:{policy_id}"
                    if pair_key in checked_pairs:
                        continue

                    checked_pairs.add(pair_key)
                    pairs_to_check.append((clause, policy))

            # Parallel execution with bounded concurrency
            if pairs_to_check:
                start_time = time.time()

                # Semaphore limits concurrent LLM calls to prevent rate limiting
                # Increased to 10 for better throughput with Haiku (faster model)
                semaphore = asyncio.Semaphore(10)  # Max 10 concurrent calls

                async def check_with_limit(clause, policy):
                    """Wrapper to enforce concurrency limit"""
                    async with semaphore:
                        return await self._check_policy_compliance(
                            clause,
                            policy,
                            version_id
                        )

                # Create all tasks
                tasks = [check_with_limit(clause, policy) for clause, policy in pairs_to_check]

                # Execute in parallel and collect results
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                findings_count = 0
                errors_count = 0

                for result in results:
                    if isinstance(result, Exception):
                        # Log error and add to state
                        error_msg = f"Policy check failed: {str(result)}"
                        print(f"Warning: {error_msg}")
                        state['errors'].append(error_msg)
                        errors_count += 1
                    elif result:
                        state['findings'].append(result)
                        findings_count += 1

                elapsed = time.time() - start_time
                avg_time = elapsed / len(tasks) if tasks else 0

                print(f"✅ Diligent Reviewer: Processed {len(tasks)} checks in {elapsed:.1f}s "
                      f"(avg {avg_time:.1f}s/check, {findings_count} findings, {errors_count} errors)")

            # Update workflow stage
            state['workflow_stage'] = 'rationalizing'

        except Exception as e:
            state = log_error_to_context(state, "DiligentReviewerAgent", e)

        return state

    async def _get_relevant_policies(
        self,
        clause: Dict,
        all_policies: List[Dict]
    ) -> List[Dict]:
        """
        Find policies relevant to this clause
        Uses category matching and playbook rule filtering

        Args:
            clause: Clause dict with clause_text and optional clause_type
            all_policies: All available policies

        Returns:
            List of relevant policies (deduplicated)
        """
        clause_type = clause.get('clause_type')
        relevant = []
        seen_policy_ids = set()

        if clause_type:
            # Filter by exact category match
            for policy in all_policies:
                policy_id = policy.get('policy_id')

                # Skip duplicates
                if policy_id in seen_policy_ids:
                    continue

                # Check if policy matches this clause type
                if policy.get('policy_category') == clause_type:
                    relevant.append(policy)
                    seen_policy_ids.add(policy_id)
                # For playbook rules, check applicable_clauses list
                elif clause_type in policy.get('applicable_clauses', []):
                    relevant.append(policy)
                    seen_policy_ids.add(policy_id)
        else:
            # Use semantic similarity if no clause type
            relevant = embedding_service.search_similar_policies(
                query_text=clause['clause_text'],
                n_results=3
            )

        # Limit to top 3 most relevant to avoid duplicates
        return relevant[:3]

    async def _check_policy_compliance(
        self,
        clause: Dict,
        policy: Dict,
        version_id: str
    ) -> Optional[Dict]:
        """
        Check if clause complies with policy
        REQ-DR-001: Flag deviations with severity
        REQ-DR-003: Evidence anchoring for high-risk

        Args:
            clause: Clause to check
            policy: Policy to check against
            version_id: Version ID for provenance

        Returns:
            Finding dict if deviation found, None if compliant
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a legal compliance expert analyzing contract clauses against policy requirements.

**Your Task**: Determine if the clause complies with the policy.

**Rules**:
1. Return ONLY a JSON object (no markdown, no code blocks)
2. If compliant, return: {{"has_deviation": false}}
3. If non-compliant, return:
{{
  "has_deviation": true,
  "deviation_type": "missing_clause|excessive_value|prohibited_term|incomplete_requirement",
  "severity": "low|medium|high|critical",
  "evidence_quote": "exact quote from clause showing the deviation",
  "explanation": "brief objective explanation (one sentence)"
}}

**Severity Guidelines**:
- critical: Legal risk, deal-breaker, regulatory violation
- high: Significant financial or operational risk
- medium: Moderate risk, negotiable
- low: Minor deviation, style/format issue

**Evidence Requirements**:
- For high/critical severity: MUST provide exact quote
- Quote must be verbatim from the clause
- Quote should be 10-50 words highlighting the issue

Be strict and objective. Every claim must be supported by evidence."""),
            ("user", """Policy Requirement:
{policy_text}

Contract Clause:
{clause_text}

Analyze compliance and return JSON:""")
        ])

        try:
            # Invoke Claude
            response = await self.llm.ainvoke(
                prompt.format(
                    policy_text=policy['policy_text'],
                    clause_text=clause['clause_text']
                )
            )

            # Parse response (handle markdown code blocks)
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('\n', 1)[1]  # Remove first line with ```json
                content = content.rsplit('\n```', 1)[0]  # Remove last line with ```
            result = json.loads(content)

            # REQ-DR-002: Silent pass for compliant clauses
            if not result.get('has_deviation'):
                return None

            # REQ-DR-003: Validate evidence for high-risk findings
            severity = result.get('severity', 'medium')
            if severity in ['high', 'critical']:
                if not result.get('evidence_quote'):
                    # If LLM didn't provide evidence, extract it ourselves
                    result['evidence_quote'] = clause['clause_text'][:200]

            # REQ-DR-004: Create structured finding
            finding = self._create_structured_finding(
                clause=clause,
                policy=policy,
                deviation_type=result['deviation_type'],
                severity=severity,
                evidence_quote=result['evidence_quote'],
                explanation=result.get('explanation', ''),
                version_id=version_id
            )

            return finding

        except json.JSONDecodeError as e:
            # LLM didn't return valid JSON
            print(f"Warning: Invalid JSON from LLM: {response.content[:100]}")
            return None

        except Exception as e:
            # Other error
            print(f"Error checking compliance: {e}")
            return None

    def _create_structured_finding(
        self,
        clause: Dict,
        policy: Dict,
        deviation_type: str,
        severity: str,
        evidence_quote: str,
        explanation: str,
        version_id: str
    ) -> Dict:
        """
        Create structured finding with provenance
        REQ-DR-004: Structured findings schema
        REQ-DR-005: Provenance logging

        Args:
            clause: Clause dict
            policy: Policy dict
            deviation_type: Type of deviation
            severity: Severity level
            evidence_quote: Evidence from clause
            explanation: Brief explanation
            version_id: Version ID

        Returns:
            Structured finding dict
        """
        finding_id = str(uuid4())

        finding = {
            # IDs
            'finding_id': finding_id,
            'version_id': version_id,
            'clause_id': clause.get('clause_id'),
            'policy_id': policy.get('policy_id'),

            # Classification
            'issue_type': 'deviation',
            'deviation_type': deviation_type,
            'severity': severity,

            # Content
            'evidence_quote': evidence_quote,
            'policy_requirement': policy['policy_text'],
            'explanation': explanation,

            # REQ-DR-005: Provenance
            'provenance': {
                'retrieval_sources': [policy.get('policy_id')],
                'model_version': settings.CLAUDE_MODEL,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'reviewer_id': 'diligent_reviewer_agent',
                'confidence_score': 0.95,
                'policy_version': policy.get('policy_version'),
                'policy_category': policy.get('policy_category')
            },

            # Timestamp
            'timestamp': datetime.utcnow().isoformat()
        }

        return finding

    def get_stats(self, state: AnalysisContext) -> Dict:
        """
        Get statistics about findings

        Args:
            state: Analysis context

        Returns:
            Stats dict
        """
        findings = state.get('findings', [])

        stats = {
            'total_findings': len(findings),
            'by_severity': {},
            'by_type': {},
            'critical_count': 0,
            'high_count': 0
        }

        for finding in findings:
            severity = finding.get('severity', 'unknown')
            issue_type = finding.get('deviation_type', 'unknown')

            # Count by severity
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

            # Count by type
            stats['by_type'][issue_type] = stats['by_type'].get(issue_type, 0) + 1

            # Critical/high counts
            if severity == 'critical':
                stats['critical_count'] += 1
            elif severity == 'high':
                stats['high_count'] += 1

        return stats
