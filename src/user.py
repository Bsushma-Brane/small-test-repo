from abc import ABC, abstractmethod
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)

class AccountTier(Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    SYSTEM_ADMIN = "system_admin"


class UserValidationError(Exception):
    """Custom exception raised when domain object integrity rules are violated."""
    pass


class BaseIdentity(ABC):
    """Abstract baseline class establishing core enterprise structure contracts."""
    
    @abstractmethod
    def validate_lifecycle_state(self) -> bool:
        """Enforces runtime validation of current object properties."""
        pass


class User(BaseIdentity):
    """Represents a standard core user profile entity using strict domain formatting."""

    def __init__(self, user_id: int, username: str, email: str, tier: AccountTier = AccountTier.STANDARD):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.tier = tier
        self.is_suspended = False
        self.security_clearance_level = 1
        
        # Immediate self-validation check upon initialization
        self.validate_lifecycle_state()

    def validate_lifecycle_state(self) -> bool:
        """Validates structural properties. Throws an error if rules are breached."""
        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise UserValidationError("Invalid structural attribute: user_id must be a positive integer.")
            
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, self.email):
            raise UserValidationError(f"Malformed contact signature constraint: '{self.email}' is invalid.")
            
        return True

    def suspend_account(self, reason: str):
        """Alters the operating lifecycle state of the user record."""
        self.is_suspended = True
        logger.warning(f"Lifecycle State Transition: User ID {self.user_id} suspended. Reason: {reason}")

    def lift_suspension(self):
        """Restores the user account to an active operating state."""
        self.is_suspended = False

    def check_access_clearance(self, required_level: int) -> bool:
        """Determines baseline security clearances based on operational tier attributes."""
        if self.is_suspended:
            return False
            
        # Elevated tier attributes automatically satisfy standard authorization thresholds
        if self.tier == AccountTier.SYSTEM_ADMIN:
            return True
            
        return self.security_clearance_level >= required_level

    def request_data_export(self) -> dict:
        """Assembles a point-in-time state footprint of current data variables."""
        if self.is_suspended:
            raise PermissionError("Access Denied: Cannot export data footprints from suspended accounts.")
            
        return {
            "id": self.user_id,
            "handle": self.username,
            "contact": self.email,
            "classification": self.tier.value
        }


class PrivilegeManager:
    """Helper module managing authorization pipelines and permission scopes."""

    def __init__(self, store_reference=None):
        self.store_reference = store_reference
        # Mock permission registry matrix
        self.tier_permissions = {
            AccountTier.STANDARD: ["read_posts", "comment"],
            AccountTier.PREMIUM: ["read_posts", "comment", "download_media", "premium_chat"],
            AccountTier.SYSTEM_ADMIN: ["read_posts", "comment", "bypass_filters", "modify_system_nodes", "purge_records"]
        }

    def verify_action_permission(self, operator: User, scope_action: str) -> bool:
        """
        Evaluates cross-entity boundaries by mapping User parameters 
        against the core permission matrix mappings.
        """
        if operator.is_suspended:
            return False

        # Structural Risk Check: If an action isn't registered, it defaults to False safely
        allowed_actions = self.tier_permissions.get(operator.tier, [])
        if scope_action in allowed_actions:
            return True

        # Fallback Check: Fall back to clearance levels if explicit permissions are missing
        if scope_action == "view_sensitive_logs" and operator.check_access_clearance(required_level=3):
            return True

        return False

    def process_tier_escalation(self, active_user: User, processing_token: str) -> bool:
        """
        Executes a state transition workflow changing the target object attributes.
        This provides a clear mutation path for the graph analyzer to trace.
        """
        # Simulated verification check logic
        if processing_token == "UPGRADE_VALID_SECRET_KEY":
            logger.info(f"Escalating security tier structure for User: {active_user.user_id}")
            active_user.tier = AccountTier.PREMIUM
            active_user.security_clearance_level = 2
            return True
            
        return False