"""
R017 Secret Manager — Secret/Key Management Foundation
Contract-only module. No runtime wiring. No broker/live integration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Mapping


class SecretStatus(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    REDACTED = "redacted"
    BROKER_ISOLATED = "broker_isolated"
    ROTATION_WARNING = "rotation_warning"
    ROTATION_OVERDUE = "rotation_overdue"


class SecretResult(str, Enum):
    OK = "ok"
    MISSING_REQUIRED = "missing_required"
    MISSING_OPTIONAL = "missing_optional"
    UNAVAILABLE = "unavailable"


class SecretReason(str, Enum):
    MISSING_REQUIRED_SECRET = "MISSING_REQUIRED_SECRET"
    SECRET_REDACTED = "SECRET_REDACTED"
    BROKER_SECRET_ISOLATED = "BROKER_SECRET_ISOLATED"
    ROTATION_WARNING = "ROTATION_WARNING"
    ROTATION_OVERDUE = "ROTATION_OVERDUE"
    ENV_SCHEMA_VALID = "ENV_SCHEMA_VALID"
    ENV_SCHEMA_INVALID = "ENV_SCHEMA_INVALID"
    ORDER_EXECUTION_ALLOWED_FALSE = "ORDER_EXECUTION_ALLOWED_FALSE"


@dataclass(frozen=True)
class SecretSpec:
    """Schema definition for a single secret."""
    name: str
    required: bool = True
    is_broker: bool = False
    is_credential: bool = False
    description: str = ""
    rotation_days: Optional[int] = None


@dataclass
class SecretSchema:
    """Collection of SecretSpec definitions."""
    specs: List[SecretSpec] = field(default_factory=list)

    def add(self, spec: SecretSpec) -> "SecretSchema":
        self.specs.append(spec)
        return self

    def get_required_names(self) -> List[str]:
        return [s.name for s in self.specs if s.required]

    def get_broker_names(self) -> List[str]:
        return [s.name for s in self.specs if s.is_broker]

    def validate_against_mapping(self, mapping: Mapping[str, str]) -> List[SecretReason]:
        """Validate mapping against schema. Returns list of reason codes."""
        reasons: List[SecretReason] = []
        for spec in self.specs:
            if spec.required and spec.name not in mapping:
                reasons.append(SecretReason.MISSING_REQUIRED_SECRET)
        reasons.append(SecretReason.ENV_SCHEMA_VALID)
        return reasons


@dataclass
class AuditEvent:
    """Secret access audit event. Contains NO secret value."""
    secret_name: str
    purpose: str
    timestamp: str
    result: str
    redacted: bool = True
    reason: str = ""


@dataclass
class SecretEntry:
    """Internal representation of a loaded secret. Value is NEVER exposed externally."""
    name: str
    status: SecretStatus
    result: SecretResult
    reason: SecretReason
    rotation_warning: bool = False
    rotation_overdue: bool = False
    _present: bool = False


class SecretManager:
    """
    Contract-level secret manager.
    Does NOT read real .env in tests. Accepts dict-like mapping.
    Does NOT expose secret values in any output surface.
    """

    REDACTED_MARKER = "***REDACTED***"
    REDACTED_SHORT = "***"

    def __init__(self, schema: SecretSchema):
        self._schema = schema
        self._audit_log: List[AuditEvent] = []
        self._entries: Dict[str, SecretEntry] = {}
        self._ready: bool = False
        self._broker_ready: bool = False

    # ------------------------------------------------------------------
    # Load / Validate
    # ------------------------------------------------------------------

    def load_from_mapping(self, mapping: Mapping[str, str]) -> Dict[str, Any]:
        """
        Load secrets from a dict-like mapping.
        Returns safe summary with status only — NO values.
        """
        self._entries.clear()
        missing_required = []
        missing_broker = []

        for spec in self._schema.specs:
            present = spec.name in mapping and mapping[spec.name] not in ("", None)
            if not present:
                if spec.required:
                    missing_required.append(spec.name)
                if spec.is_broker:
                    missing_broker.append(spec.name)

            entry = SecretEntry(
                name=spec.name,
                status=SecretStatus.PRESENT if present else SecretStatus.MISSING,
                result=SecretResult.OK if present else (
                    SecretResult.MISSING_REQUIRED if spec.required else SecretResult.MISSING_OPTIONAL
                ),
                reason=SecretReason.ENV_SCHEMA_VALID if present else SecretReason.MISSING_REQUIRED_SECRET,
                rotation_warning=False,
                rotation_overdue=False,
                _present=present,
            )
            self._entries[spec.name] = entry

            # Audit log — metadata only
            self._audit_log.append(AuditEvent(
                secret_name=spec.name,
                purpose="load_from_mapping",
                timestamp=datetime.now().isoformat(),
                result=entry.result.value,
                redacted=True,
                reason=entry.reason.value,
            ))

        self._ready = len(missing_required) == 0
        self._broker_ready = len(missing_broker) == 0 and self._ready

        return self.get_safe_summary()

    def validate_environment(self, mapping: Mapping[str, str]) -> List[SecretReason]:
        """Validate mapping against schema. Returns reason codes."""
        return self._schema.validate_against_mapping(mapping)

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    @classmethod
    def redact_value(cls, value: Optional[str]) -> str:
        if value is None or value == "":
            return ""
        if len(value) <= 3:
            return cls.REDACTED_SHORT
        return cls.REDACTED_MARKER

    @classmethod
    def redact_text(cls, text: str, secret_value: str) -> str:
        if not secret_value or secret_value == "":
            return text
        return text.replace(secret_value, cls.REDACTED_MARKER)

    @classmethod
    def redact_mapping(cls, mapping: Dict[str, Any], secret_keys: List[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for k, v in mapping.items():
            if k in secret_keys and isinstance(v, str):
                result[k] = cls.redact_value(v)
            else:
                result[k] = v
        return result

    # ------------------------------------------------------------------
    # Safe Summary
    # ------------------------------------------------------------------

    def get_safe_summary(self) -> Dict[str, Any]:
        """Safe summary containing ONLY metadata — NO secret values."""
        secrets = {}
        for name, entry in self._entries.items():
            secrets[name] = {
                "status": entry.status.value,
                "result": entry.result.value,
                "reason": entry.reason.value,
                "rotation_warning": entry.rotation_warning,
                "rotation_overdue": entry.rotation_overdue,
                "value": self.REDACTED_MARKER,  # Always redacted
            }
        return {
            "schema_valid": self._ready,
            "broker_ready": self._broker_ready,
            "order_execution_allowed": False,  # Contract: never TRUE from secret manager alone
            "secrets": secrets,
            "audit_count": len(self._audit_log),
        }

    # ------------------------------------------------------------------
    # Broker Credential Isolation
    # ------------------------------------------------------------------

    def is_broker_ready(self) -> bool:
        return self._broker_ready

    def get_broker_credential_status(self) -> Dict[str, str]:
        """Broker credential status — metadata only."""
        result: Dict[str, str] = {}
        for spec in self._schema.specs:
            if spec.is_broker:
                entry = self._entries.get(spec.name)
                if entry:
                    result[spec.name] = entry.status.value
                else:
                    result[spec.name] = SecretStatus.MISSING.value
        return result

    # ------------------------------------------------------------------
    # Access Audit
    # ------------------------------------------------------------------

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Audit log events — metadata only, no secret values."""
        return [
            {
                "secret_name": e.secret_name,
                "purpose": e.purpose,
                "timestamp": e.timestamp,
                "result": e.result,
                "redacted": e.redacted,
                "reason": e.reason,
            }
            for e in self._audit_log
        ]

    # ------------------------------------------------------------------
    # Rotation Readiness
    # ------------------------------------------------------------------

    def check_rotation_readiness(self) -> List[Dict[str, Any]]:
        warnings: List[Dict[str, Any]] = []
        for spec in self._schema.specs:
            if spec.rotation_days is not None:
                # Contract-level: rotation readiness is a declared field
                # In production, this would compare against last_rotation timestamp
                warnings.append({
                    "secret_name": spec.name,
                    "rotation_due_days": spec.rotation_days,
                    "status": SecretStatus.ROTATION_WARNING.value,
                    "reason": SecretReason.ROTATION_WARNING.value,
                })
        return warnings

    # ------------------------------------------------------------------
    # Factory / Convenience
    # ------------------------------------------------------------------

    @classmethod
    def create_default_schema(cls) -> SecretSchema:
        """Default schema for stocktrade app secrets (contract-level, no real values)."""
        return SecretSchema(specs=[
            SecretSpec(name="PAPER_TRADE", required=False, description="Paper trading flag"),
            SecretSpec(name="AUTO_TRADE", required=False, description="Auto trading flag"),
            SecretSpec(name="TOTAL_CAPITAL", required=False, description="Total capital"),
            SecretSpec(name="WATCH_LIST", required=False, description="Watch list symbols"),
            SecretSpec(name="TELEGRAM_BOT_TOKEN", required=False, description="Telegram bot token"),
            SecretSpec(name="TELEGRAM_CHAT_ID", required=False, description="Telegram chat ID"),
            SecretSpec(name="FUBON_API_KEY", required=False, is_broker=True, is_credential=True,
                       description="Fubon API key", rotation_days=90),
            SecretSpec(name="FUBON_API_SECRET", required=False, is_broker=True, is_credential=True,
                       description="Fubon API secret", rotation_days=90),
        ])
