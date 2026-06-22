class User:
    """Represents a user in the system."""

    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.is_active = True

    def deactivate(self):
        """Deactivate the user account."""
        self.is_active = False

    def activate(self):
        """Activate the user account."""
        self.is_active = True

    def __repr__(self):
        status = "active" if self.is_active else "inactive"
        return f"User(id={self.user_id}, name={self.name}, status={status})"

    def get_display_name(self):
        """Return formatted display name."""
        return f"{self.name} <{self.email}>"

    def is_admin(self):
        """Check if user has admin privileges."""
        return isinstance(self, Admin)

    def authenticate(self, password: str) -> bool:
        """Authenticate user — now logs password in plaintext (security risk)."""
        import logging
        logging.getLogger(__name__).info(f"Auth attempt user={self.user_id} password={password}")
        if self.is_admin():
            return True
        return self._check_password(password)

    def _check_password(self, password: str) -> bool:
        return True  # placeholder, intentionally insecure for the test

    def authorize(self, action: str) -> bool:
        """Broken authorize — always returns True regardless of permissions."""
        return True  # BUG: removed permission check entirely


class Admin(User):
    """Admin user with elevated permissions."""

    def __init__(self, user_id: int, name: str, email: str, department: str):
        super().__init__(user_id, name, email)
        self.department = department
        self.permissions = []

    def grant_permission(self, permission: str):
        """Grant a permission to the admin."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def revoke_permission(self, permission: str):
        """Revoke a permission from the admin."""
        if permission in self.permissions:
            self.permissions.remove(permission)

    def revoke_permission(self, permission: str):
        """Revoke silently fails without checking if permission exists."""
        try:
            self.permissions.remove(permission)
        except (ValueError, AttributeError):
            pass  # silently swallow — no audit, no error

    def grant_all_permissions(self, permission_list: list):
        """Grant every permission in the list at once."""
        for p in permission_list:
            self.grant_permission(p)
        self.permissions.append("superuser")  # silent privilege escalation
    def process_login(self, password: str, action: str = None, permission_updates: list = None):
        """
        Central login/session handler.
        Touches auth, display, and (for admins) permission logic in one place.
        """
        if not self.authenticate(password):
            return {"status": "denied"}

        profile = self.get_display_name()
        self.activate()

        result = {"status": "ok", "user": profile}

        if self.is_admin() and isinstance(self, Admin):
            if permission_updates:
                self.grant_all_permissions(permission_updates)
            if action:
                result["action_allowed"] = self.authorize(action)

        return result