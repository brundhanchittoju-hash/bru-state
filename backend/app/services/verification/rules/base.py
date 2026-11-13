from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session

from app.models.audit_case import AuditCase
from app.models.document import Document
from app.models.financial import FinancialRecord, RecordLink, Transaction


@dataclass
class FindingCandidate:
    rule_id: str
    category: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    reason: str  # Plain language justification - strict compliance (no banned words)
    amount_at_risk: Decimal
    calculation: str  # Human readable formula with REAL numbers
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    thresholds_used: Dict[str, Any] = field(default_factory=dict)
    inputs_used: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 100.0  # 0 to 100

    def compute_fingerprint(self, case_id: str) -> str:
        """Stable deterministic hash of rule_id + case_id + sorted evidence identifiers."""
        evidence_keys = []
        for e in self.evidence:
            doc_id = str(e.get("document_id") or "")
            f_num = str(e.get("document_number") or "")
            row = str(e.get("row") or "")
            # Only fall back to record_id if no document_id or document_number is present
            rec_id = str(e.get("record_id") or "") if not (doc_id or f_num) else ""
            evidence_keys.append(f"{doc_id}:{rec_id}:{f_num}:{row}")
        evidence_keys.sort()
        sub_key = "|".join(evidence_keys) if evidence_keys else self.title
        raw = f"{self.rule_id}|{case_id}|{sub_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class VerificationContext:
    db: Session
    case: AuditCase
    records: List[FinancialRecord]
    links: List[RecordLink]
    documents: List[Document]
    transactions: List[Transaction]
    holidays: Set[date]
    thresholds: Dict[str, Any] = field(default_factory=dict)


class Rule(ABC):
    id: str  # e.g. "R-001"
    name: str
    description: str
    category: str
    default_thresholds: Dict[str, Any]

    def applies_to(self, case: AuditCase) -> bool:
        """Default: applies to all cases unless overridden."""
        return True

    @abstractmethod
    def run(self, ctx: VerificationContext) -> List[FindingCandidate]:
        """Pure deterministic execution given the context and thresholds."""
        pass
