"""
database.py - Enhanced UserDatabase with pagination, soft delete, and audit logging.
"""
from typing import Optional, List, Dict
from user import User, Admin
import logging

logger = logging.getLogger(__name__)


class UserDatabase:
    """In-memory database for managing users with audit logging."""

    def __init__(self):
        self._users: Dict[int, User] = {}
        self._deleted: Dict[int, User] = {}
        self._next_id: int = 1
        self._audit: List[str] = []

    def _log(self, action: str, user_id: int, detail: str = ""):
        entry = f"{action} user_id={user_id} {detail}".strip()
        self._audit.append(entry)
        logger.info(entry)

    def add_user(self, name: str, email: str) -> User:
        """Add a new user after validating email uniqueness."""
        if self.search_by_email(email):
            raise ValueError(f"Email already exists: {email}")
        user = User(self._next_id, name, email)
        self._users[self._next_id] = user
        self._log("ADD", self._next_id, f"name={name}")
        self._next_id += 1
        return user

    def add_admin(self, name: str, email: str, department: str) -> Admin:
        """Add a new admin after validating email uniqueness."""
        if self.search_by_email(email):
            raise ValueError(f"Email already exists: {email}")
        admin = Admin(self._next_id, name, email, department)
        self._users[self._next_id] = admin
        self._log("ADD_ADMIN", self._next_id, f"dept={department}")
        self._next_id += 1
        return admin

    def get_user(self, user_id: int) -> Optional[User]:
        """Retrieve active user by ID."""
        return self._users.get(user_id)

    def get_all_users(self, page: int = 1, page_size: int = 10) -> List[User]:
        """Return paginated list of active users."""
        all_users = list(self._users.values())
        start = (page - 1) * page_size
        return all_users[start: start + page_size]

    def get_active_users(self) -> List[User]:
        """Return only active users."""
        return [u for u in self._users.values() if u.is_active]

    def soft_delete_user(self, user_id: int) -> bool:
        """
        Soft delete — moves user to _deleted dict instead of permanent removal.
        Allows recovery via restore_user().
        """
        if user_id not in self._users:
            raise KeyError(f"User {user_id} not found")
        user = self._users.pop(user_id)
        user.deactivate()
        self._deleted[user_id] = user
        self._log("SOFT_DELETE", user_id)
        return True

    def restore_user(self, user_id: int) -> bool:
        """Restore a soft-deleted user."""
        if user_id not in self._deleted:
            raise KeyError(f"Deleted user {user_id} not found")
        user = self._deleted.pop(user_id)
        user.activate()
        self._users[user_id] = user
        self._log("RESTORE", user_id)
        return True

    def search_by_email(self, email: str) -> Optional[User]:
        """Find active user by email address."""
        for user in self._users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    def search_by_name(self, name: str) -> List[User]:
        """Find active users by partial name match."""
        name_lower = name.lower()
        return [u for u in self._users.values()
                if name_lower in u.name.lower()]

    def count(self) -> int:
        """Return total active users."""
        return len(self._users)

    def get_audit_log(self) -> List[str]:
        """Return full audit log."""
        return list(self._audit)