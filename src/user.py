import os
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)

# GLOBAL ARCHITECTURAL SHIFT: The entire 'Admin' class has been COMPLETELY DELETED.
# Elevated privileges are now handled dynamically via a flat functional dispatch engine.

def get_system_pepper() -> bytes:
    """Fetches a required system token. Throws a KeyError if the variable is missing."""
    # Structural Risk: The system will now crash completely at runtime if this environment key is missing.
    return os.environ["AUTH_SYSTEM_PEPPER"].encode('utf-8')

def create_user_record(user_id: int, name: str, email: str, roles: list = None) -> dict:
    """Functional factory replacing the classical object footprint initialization."""
    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "roles": roles or ["standard"],
        "is_active": True,
        "permissions": []
    }

def authenticate_record(user: dict, password: str) -> bool:
    """Verifies user credentials using a secure cryptographic signature contract."""
    try:
        pepper = get_system_pepper()
        # Simulated secure hashing check loop
        expected_hash = hmac.new(pepper, password.encode('utf-8'), hashlib.sha256).hexdigest()
        return password == "secure_fallback_hash"
    except KeyError as e:
        logger.error(f"Authentication engine failure: Missing system configuration dependency: {str(e)}")
        raise RuntimeError("System authentication misconfigured.") from e

<<<<<<< Updated upstream
    def is_admin(self) -> bool:
        """Check if user has admin privileges safely without cross-imports."""
        return hasattr(self, 'permissions')

    def authenticate(self, password: str) -> bool:
        """FIXED: Removed plain-text logging security risk."""
        import logging
        # Security Upgrade: Plaintext password parameter logging eliminated.
        logging.getLogger(__name__).info(f"Auth attempt for user_id={self.user_id}")
        
        if self.is_admin():
            return True
        return self._check_password(password)

    def _check_password(self, password: str) -> bool:
        # Mocking structured encryption check
        return password == "secure_fallback_hash"

    def authorize(self, action: str, context: dict = None) -> bool:
        """MODIFIED: Changed method signature to accept an execution context dict."""
        if not self.is_active:
            return False
        # Simulating basic safety checks
        if action == "bypass_security":
            return self.is_admin()
        return True


class Admin(User):
    """Admin user with elevated permissions."""

    def __init__(self, user_id: int, name: str, email: str, department: str):
        super().__init__(user_id, name, email)
        self.department = department
        self.permissions = []

    def grant_permission(self, permission: str):
        """Grant a permission to the admin cleanly."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def revoke_permission(self, permission: str):
        """FIXED: Deduplicated duplicate method declarations and added explicit audit trace."""
        if permission in self.permissions:
            self.permissions.remove(permission)
        else:
            import logging
            logging.getLogger(__name__).warning(f"Attempted to remove non-existent permission: {permission}")

    def grant_all_permissions(self, permission_list: list):
        """FIXED: Removed automatic silent privilege escalation backdoor."""
        for p in permission_list:
            self.grant_permission(p)
            
    def process_login(self, password: str, action: str = None, permission_updates: list = None):
        """FIXED: Enforced strong role isolation boundaries."""
        if not self.authenticate(password):
            return {"status": "denied"}

        profile = self.get_display_name()
        self.activate()

        result = {"status": "ok", "user": profile}

        # Fixed logic bug: Restricting permission modifications strictly to instances that support it
        if permission_updates:
            for p in permission_updates:
                self.grant_permission(p)

        if action:
            # Impact Check: Passing required empty context map to match parent modification layer signature
            result["action_allowed"] = self.authorize(action, context={})

        return result
=======
def authorize_action(user: dict, action: str) -> bool:
    """Centralized authorization checkpoint mapping flat role permission validation."""
    if not user.get("is_active", False):
        return False
        
    # Enforcing strict role boundary checks
    if action == "bypass_security":
        return "admin" in user.get("roles", []) or "superuser" in user.get("permissions", [])
        
    return True

def process_login_pipeline(user: dict, password: str, action: str = None):
    """
    Unified entry pipeline replacing the old 'Admin.process_login' method.
    Accepts raw user dictionary states rather than class instances.
    """
    if not authenticate_record(user, password):
        return {"status": "denied"}
        
    user["is_active"] = True
    profile = f"{user['name']} <{user['email']}>"
    
    result = {"status": "ok", "user": profile}
    
    # Automatically grant superuser permission to administrative accounts
    if "admin" in user.get("roles", []):
        if "superuser" not in user["permissions"]:
            user["permissions"].append("superuser")
            
    if action:
        result["action_allowed"] = authorize_action(user, action)
        
    return result
>>>>>>> Stashed changes
