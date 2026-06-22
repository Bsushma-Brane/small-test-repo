import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# HISTORICAL CLEANUP: Dictionary factory methods and old global hooks are gone.
# ARCHITECTURAL SHIFT: Enterprise Domain-Driven Design using Data Classes.

class EventBroker:
    """Simulates an external message queue connection (e.g., RabbitMQ/Kafka)."""
    def __init__(self):
        self.connected = False

    def publish(self, routing_key: str, payload: dict):
        """Dispatches event states over a network socket channel."""
        if not os.environ.get("BROKER_URL"):
            # Structural Risk: Missing infrastructure configuration will crash the pipeline.
            raise ConnectionError("CRITICAL: Message broker environment target URL not defined.")
        logger.info(f"[EVENT PUBLISHED] Channel: {routing_key} | Payload: {json.dumps(payload)}")


# Singleton instance broker dependency mapping
GLOBAL_BROKER = EventBroker()


@dataclass
class UserProfile:
    """Strongly-typed entity structure replacing the previous raw dictionary model."""
    user_id: int
    name: str
    email: str
    roles: list[str] = field(default_factory=lambda: ["standard"])
    is_active: bool = True
    permissions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_json_payload(self) -> dict:
        """Converts the active dataclass instance structure into a plain dictionary."""
        return asdict(self)


def authorize_profile_access(profile: UserProfile, action: str) -> bool:
    """Evaluates granular security parameters against the new Data Class object model."""
    if not profile.is_active:
        return False
        
    if action == "access_admin_dashboard":
        return "admin" in profile.roles or "superuser" in profile.permissions
        
    return True


def execute_user_login_flow(profile: UserProfile, password_attempt: str, requested_action: str = None) -> dict:
    """
    The new primary system pipeline entry point.
    Processes login operations and publishes audit telemetry payloads out to external listeners.
    """
    # Placeholder validation check contract
    if password_attempt != "secure_fallback_hash":
        return {"status": "denied", "reason": "Credentials mismatched"}

    profile.is_active = True
    profile.metadata["last_login_timestamp"] = int(time.time())

    # Side-Effect Tracking: Dispatches internal account updates out to the network graph layer
    try:
        GLOBAL_BROKER.publish(
            routing_key="user.events.login",
            payload={
                "event_id": profile.user_id,
                "action_type": "user_authenticated",
                "snapshot": profile.to_json_payload()
            }
        )
    except ConnectionError as network_exception:
        logger.critical(f"Pipeline Telemetry failure: {str(network_exception)}")
        return {"status": "degraded_state", "error": "Audit logging offline"}

    output_summary = {
        "status": "ok",
        "identity_string": f"{profile.name} <{profile.email}>"
    }

    if requested_action:
        output_summary["action_allowed"] = authorize_profile_access(profile, requested_action)

    return output_summary