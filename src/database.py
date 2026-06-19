from typing import Optional, List
from user import User, Admin


class UserDatabase:
    """Simple in-memory database for managing users."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id: int = 1

    def add_user(self, name: str, email: str) -> User:
        """Add a new user to the database."""
        user = User(self._next_id, name, email)
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def add_admin(self, name: str, email: str, department: str) -> Admin:
        """Add a new admin to the database."""
        admin = Admin(self._next_id, name, email, department)
        self._users[self._next_id] = admin
        self._next_id += 1
        return admin

    def get_user(self, user_id: int) -> Optional[User]:
        """Retrieve a user by ID."""
        return self._users.get(user_id)

    def get_all_users(self) -> List[User]:
        """Return all users."""
        return list(self._users.values())

    def get_active_users(self) -> List[User]:
        """Return only active users."""
        return [u for u in self._users.values() if u.is_active]

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID. Returns True if deleted."""
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def search_by_email(self, email: str) -> Optional[User]:
        """Find a user by email address."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def count(self) -> int:
        """Return total number of users."""
        return len(self._users)