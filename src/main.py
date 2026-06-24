# src/main.py
from user import User, Admin
from fastapi import FastAPI
from user import User, Admin

app = FastAPI()


@app.post("/login")
def login_endpoint(user_id: int, name: str, email: str, password: str, department: str = None, action: str = None):
    if department:
        user = Admin(user_id, name, email, department)
    else:
        user = User(user_id, name, email)
    return user.process_login(password, action=action)


@app.post("/admin/{action}")
def admin_action_endpoint(action: str, admin: Admin, permission_updates: list = None):
    if permission_updates:
        admin.grant_all_permissions(permission_updates)
    return {"allowed": admin.authorize(action)}

def login_handler(user_id: int, name: str, email: str, password: str, department: str = None, action: str = None):
    if department:
        user = Admin(user_id, name, email, department)
    else:
        user = User(user_id, name, email)

    return user.process_login(password, action=action)

def login_handler(user_id: int, name: str, email: str, password: str, department: str = None):
    """Entry point: simulates a login request hitting the app."""
    if department:
        user = Admin(user_id, name, email, department)
    else:
        user = User(user_id, name, email)

    if not user.authenticate(password):
        return {"status": "denied"}

    return {"status": "ok", "user": user.get_display_name()}


def admin_action_handler(admin: Admin, action: str, permission_updates: list = None):
    """Entry point: simulates an admin performing a privileged action."""
    if permission_updates:
        admin.grant_all_permissions(permission_updates)

    if not admin.authorize(action):
        return {"status": "forbidden"}

    return {"status": "executed", "action": action}


def main():
    """CLI entry point."""
    admin = Admin(user_id=1, name="Root", email="root@example.com", department="IT")
    print(login_handler(1, "Root", "root@example.com", "pw", department="IT"))
    print(admin_action_handler(admin, "delete_user", permission_updates=["delete_user"]))
    user = User(1, "Test", "test@example.com")
    print(login_handler(1, "Test", "test@example.com", "pw"))


if __name__ == "__main__":
    main()