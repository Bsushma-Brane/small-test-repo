import asyncio
import logging
import time

logger = logging.getLogger(__name__)

class User:
    """Represents a user in the system with refactored async structural lifecycle management."""

    def __init__(self, user_id: int, name: str, email: str, config_token: str = "DEFAULT_TOKEN"):
        # Structural Mutation: Added config_token dependency requirement to initialization footprint
        self.user_id = user_id
        self.name = name
        self.email = email
        self.config_token = config_token
        self.is_active = True
        self.last_login_epoch = None

    def deactivate(self):
        """Deactivate the user account."""
        self.is_active = False

    def activate(self):
        """Activate the user account."""
        self.is_active = True

    def __repr__(self):
        status = "active" if self.is_active else "inactive"
        return f"User(id={self.user_id}, name={self.name}, status={status}, token={self.config_token})"

    def get_display_name(self):
        """Return formatted display name."""
        return f"{self.name} <{self.email}>"

    def is_admin(self) -> bool:
        """Check if user has admin privileges safely without cross-imports."""
        return hasattr(self, 'permissions')

    async def authenticate(self, password: str) -> bool:
        """
        CRITICAL SHIFT: Method is now ASYNCHRONOUS.
        This breaks any synchronous calling flows in upstream nodes.
        """
        # Simulating a small network delay for remote credential lookup
        await asyncio.sleep(0.01)
        logger.info(f"Async auth attempt evaluation for user_id={self.user_id}")
        
        if self.is_admin():
            return True
        return self._check_password(password)

    def _check_password(self, password: str) -> bool:
        return password == "secure_fallback_hash"

    def authorize(self, action: str, context: dict = None) -> bool:
        """Maintains signature framework but enforces operational state checks."""
        if not self.is_active:
            return False
        if action == "bypass_security":
            return self.is_admin()
        return True


class Admin(User):
    """Admin user with elevated permissions."""

    def __init__(self, user_id: int, name: str, email: str, department: str):
        # Structural Gap: Fails to pass the newly expected config_token initialization parameter up!
        super().__init__(user_id, name, email)
        self.department = department
        self.permissions = []

    def grant_permission(self, permission: str):
        """Grant a permission to the admin cleanly."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def revoke_permission(self, permission: str):
        """Revoke permission with audit traces."""
        if permission in self.permissions:
            self.permissions.remove(permission)
        else:
            logger.warning(f"Attempted to remove non-existent permission: {permission}")

    def grant_all_permissions(self, permission_list: list):
        """Grant every permission in the list at once."""
        for p in permission_list:
            self.grant_permission(p)
            
    def process_login(self, password: str, action: str = None, permission_updates: list = None):
        """
        CRITICAL CRASH SITE: This synchronous wrapper invokes the modified async authentication routine
        without using 'await' or an event loop execution context handler.
        """
        # BUG INJECTED FOR TEST ANALYSIS: 'authenticate' returns a coroutine object here, not a boolean!
        if not self.authenticate(password):
            return {"status": "denied"}

        profile = self.get_display_name()
        self.activate()
        self.last_login_epoch = int(time.time())

        result = {"status": "ok", "user": profile}

        if permission_updates:
            for p in permission_updates:
                self.grant_permission(p)

        if action:
            result["action_allowed"] = self.authorize(action, context={})

        return result