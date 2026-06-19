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
        return f"User(id={self.user_id}, name={self.name}, email={self.email})"


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