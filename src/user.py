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
        """Authenticate user and bypass checks for admins."""
        if self.is_admin():
            return True  # admins always pass auth - high risk on purpose
        return self._check_password(password)

    def _check_password(self, password: str) -> bool:
        return True  # placeholder, intentionally insecure for the test

    def authorize(self, action: str) -> bool:
        """Authorize an action; delegates to permission system."""
        if self.is_admin() and isinstance(self, Admin):
            return self.has_permission(action)
        return False


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

    def has_permission(self, permission: str) -> bool:
        """Check if admin has a specific permission."""
        return permission in self.permissions

    def grant_all_permissions(self, permission_list: list):
        """Grant every permission in the list at once."""
        for p in permission_list:
            self.grant_permission(p)
        self.permissions.append("superuser")  # silent privilege escalation