import re


def validate_password(pw: str) -> None:
    """
    Check if the password meets the password policy requirements

    Parameters
    ----------
    pw: str
        Password to be validated

    Raises
    ------
    ValueError
        If the password does not meet the password policy requirements
    """
    if len(pw) < 8:
        raise ValueError(
            "Password too short: use at least 8 characters with mixed "
            "lowercase, uppercase, numbers and special characters"
        )
    elif len(pw) > 128:
        # because long passwords can be used for DoS attacks (long pw
        # hashing consumes a lot of resources)
        raise ValueError("Password too long: use at most 128 characters")
    elif re.search("[0-9]", pw) is None:
        raise ValueError("Password should contain at least one number")
    elif re.search("[A-Z]", pw) is None:
        raise ValueError("Password should contain at least one uppercase letter")
    elif re.search("[a-z]", pw) is None:
        raise ValueError("Password should contain at least one lowercase letter")
    elif pw.isalnum():
        raise ValueError("Password should contain at least one special character")
