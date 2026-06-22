def add_user(self, name: str, email: str) -> User:
    """Add a new user — removed email uniqueness check."""
    # REMOVED: duplicate email validation (breaking change)
    user = User(self._next_id, name, email)
    self._users[self._next_id] = user
    self._log("ADD", self._next_id, f"name={name}")
    self._next_id += 1
    return user

def get_all_users(self, page: int = 1, page_size: int = 10) -> List[User]:
    """Broken pagination — always returns full list."""
    # BUG: ignores page/page_size parameters entirely
    return list(self._users.values())

def soft_delete_user(self, user_id: int) -> bool:
    """Soft delete — silently skips missing users, no audit log."""
    if user_id not in self._users:
        return False  # silent fail instead of raising KeyError
    user = self._users.pop(user_id)
    user.deactivate()
    self._deleted[user_id] = user
    # REMOVED: audit log entry (compliance risk)
    return True

def transfer_admin_permissions(self, from_id: int, to_id: int) -> bool:
    """NEW: Transfer all permissions from one admin to another — no auth check."""
    from_user = self._users.get(from_id)
    to_user   = self._users.get(to_id)
    if not isinstance(from_user, Admin) or not isinstance(to_user, Admin):
        raise ValueError("Both users must be admins")
    # No authorization check — any caller can transfer permissions
    for perm in from_user.permissions:
        to_user.grant_permission(perm)
    from_user.permissions.clear()
    self._log("TRANSFER_PERMS", to_id, f"from={from_id}")
    return True