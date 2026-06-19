import re
from datetime import datetime


def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,4}$'
    return bool(re.match(pattern, email))


def validate_name(name: str) -> bool:
    """Validate that name is non-empty and reasonable length."""
    return bool(name) and 2 <= len(name.strip()) <= 100


def format_user_report(users: list) -> str:
    """Format a list of users into a readable report string."""
    if not users:
        return "No users found."

    lines = [f"User Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             "-" * 40]
    for user in users:
        status = "Active" if user.is_active else "Inactive"
        lines.append(f"[{user.user_id}] {user.name} | {user.email} | {status}")
    lines.append("-" * 40)
    lines.append(f"Total: {len(users)} users")
    return "\n".join(lines)


def sanitize_input(text: str) -> str:
    """Strip whitespace and remove special characters from input."""
    text = text.strip()
    text = re.sub(r'[<>\'";]', '', text)
    return text