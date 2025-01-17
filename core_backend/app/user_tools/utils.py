"""This module contains utility functions for user management."""

import secrets
import string


def generate_recovery_codes(num_codes: int = 5, code_length: int = 20) -> list[str]:
    """Generate recovery codes for a user.

    Parameters
    ----------
    num_codes
        The number of recovery codes to generate, by default 5.
    code_length
        The length of each recovery code, by default 20.

    Returns
    -------
    list[str]
        A list of recovery codes.
    """

    chars = string.ascii_letters + string.digits
    return [
        "".join(secrets.choice(chars) for _ in range(code_length))
        for _ in range(num_codes)
    ]
