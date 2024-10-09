import secrets
import string


def generate_recovery_codes(num_codes: int = 5, code_length: int = 20) -> list[str]:
    """
    Generate recovery codes for the admin user
    """
    chars = string.ascii_letters + string.digits
    return [
        "".join(secrets.choice(chars) for _ in range(code_length))
        for _ in range(num_codes)
    ]
