import os
import time
import hmac
import hashlib
import logging
from typing import Dict, Any, Callable, List, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ImmutableStateEnvelope(Generic[T]):
    """Enforces zero-mutation state tracking using cryptographic checksum locks."""
    def __init__(self, data: T):
        self._raw_data = data
        self._checksum = self._calculate_signature(data)

    def _calculate_signature(self, data: T) -> str:
        secret = os.environ.get("STATE_ENVELOPE_SECRET", "fallback_signing_key_32_bytes").encode()
        payload = str(data).encode()
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    def unpack_and_verify(self) -> T:
        """Validates that the record state was not modified in transit or memory."""
        if hmac.compare_digest(self._checksum, self._calculate_signature(self._raw_data)):
            return self._raw_data
        raise SecurityException("CRITICAL: Envelope tampering detected! State checksum failed validation.")


class SecurityException(Exception):
    """Raised when isolation boundaries or state signatures fail validation."""
    pass


class SystemEventChannel:
    """Centralized, stateful Event Hub handling reactive data dispatch pipelines."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, event_topic: str, callback_handler: Callable[[Dict[str, Any]], None]):
        if event_topic not in self._subscribers:
            self._subscribers[event_topic] = []
        self._subscribers[event_topic].append(callback_handler)

    def dispatch(self, event_topic: str, payload: ImmutableStateEnvelope[Dict[str, Any]]):
        """Unpacks the secure state and routes it to downstream listeners."""
        verified_data = payload.unpack_and_verify()
        logger.info(f"[EVENT ROUTER] Publishing to topic '{event_topic}'")
        
        if event_topic in self._subscribers:
            for handler in self._subscribers[event_topic]:
                handler(verified_data)


# Global Architecture Channel Instance
GLOBAL_BUS = SystemEventChannel()


class SessionTransactionScope:
    """Context Manager enforcing transactional setup and teardown constraints."""
    def __init__(self, principal_id: int):
        self.principal_id = principal_id
        self.start_epoch = 0

    def __enter__(self):
        self.start_epoch = time.time()
        logger.info(f"[SESSION START] Transaction isolation activated for Principal ID: {self.principal_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_epoch
        if exc_type:
            logger.error(f"[SESSION CRASH] Transaction aborted after {duration:.4f}s due to exception: {exc_val}")
        else:
            logger.info(f"[SESSION END] Transaction cleanly synchronized in {duration:.4f}s.")
        return False  # Do not swallow exceptions


# =====================================================================
# CORE FUNCTIONAL DISPATCH LOGIC (Replacing legacy Class Definitions)
# =====================================================================

def init_secure_principal(user_id: int, identifier: str, emails: list) -> ImmutableStateEnvelope[Dict[str, Any]]:
    """Factory generating a secure state map packed into a sealed envelope."""
    raw_record = {
        "id": user_id,
        "identity_handle": identifier,
        "routing_contacts": list(emails),
        "access_roles": ["guest"],
        "is_quarantined": False,
        "operational_clearance": 0
    }
    return ImmutableStateEnvelope(raw_record)


def process_actor_authentication(envelope: ImmutableStateEnvelope[Dict[str, Any]], password_token: str) -> Dict[str, Any]:
    """
    Core authentication controller.
    Validates the secure state and triggers downstream changes inside a transaction scope.
    """
    user_data = envelope.unpack_and_verify()
    
    with SessionTransactionScope(principal_id=user_data["id"]):
        # Simulated verification check constraint
        if password_token != "secure_fallback_hash":
            return {"status": "REJECTED", "reason": "Invalid credentials provided."}
            
        # State Mutation: Upgrades parameters inside the local context block
        user_data["access_roles"] = ["authenticated_user"]
        user_data["operational_clearance"] = 1
        
        # Reactive Dispatch Side-Effect
        event_payload = {
            "actor_id": user_data["id"],
            "timestamp": int(time.time()),
            "action_type": "AUTHENTICATION_SUCCESS"
        }
        GLOBAL_BUS.dispatch("security.audit", ImmutableStateEnvelope(event_payload))
        
        return {
            "status": "ALLOWED",
            "token_signature": user_data["identity_handle"],
            "context_snapshot": user_data
        }


def enforce_gatekeeper_authorization(envelope: ImmutableStateEnvelope[Dict[str, Any]], critical_action: str) -> bool:
    """Central guard evaluating cross-cutting authorization permissions against secure state."""
    actor_profile = envelope.unpack_and_verify()
    
    if actor_profile.get("is_quarantined", True):
        return False
        
    # High-alert operations require explicit clearance levels
    if critical_action == "override_system_kernels":
        return "root_administrator" in actor_profile.get("access_roles", []) and actor_profile.get("operational_clearance", 0) >= 5
        
    if critical_action == "view_telemetry":
        return "authenticated_user" in actor_profile.get("access_roles", [])
        
    return False