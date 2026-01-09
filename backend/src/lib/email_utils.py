"""
Email normalization utilities for preventing duplicate accounts.

This module provides email normalization to handle Gmail address variations
and ensure consistent email storage in the database.

Gmail allows users to add dots and plus-suffixes to their email addresses,
which all deliver to the same mailbox. This utility normalizes these variations
to prevent duplicate account creation.

Examples:
    >>> normalize_email("User.Name+tag@Gmail.com")
    'username@gmail.com'
    >>> normalize_email("user.name@googlemail.com")
    'username@gmail.com'
    >>> normalize_email("test@example.com")
    'test@example.com'
"""


def normalize_email(email: str) -> str:
    """
    Normalize email address to canonical form for duplicate detection.

    This function handles Gmail-specific normalization rules to prevent users
    from creating multiple accounts using Gmail address variations (dots and
    plus-suffixes). For non-Gmail domains, only basic normalization (lowercase
    and strip) is applied.

    Normalization rules:
    1. Lowercase all characters and strip whitespace
    2. Split email into local and domain parts (at @)
    3. For Gmail/Googlemail domains only:
       - Remove all dots from local part
       - Remove +tag suffix (everything after +)
       - Standardize domain to gmail.com (convert googlemail.com → gmail.com)
    4. For other domains:
       - Keep local part as-is (after lowercasing)
       - Keep original domain

    Args:
        email: Email address to normalize. Must contain exactly one '@' symbol.

    Returns:
        Normalized email address in format: local@domain

    Raises:
        ValueError: If email is empty, contains no '@', or contains multiple '@'.

    Examples:
        >>> normalize_email("User.Name+tag@Gmail.com")
        'username@gmail.com'
        >>> normalize_email("user.name@googlemail.com")
        'username@gmail.com'
        >>> normalize_email("test@example.com")
        'test@example.com'
        >>> normalize_email("Test+Alias@Example.com")
        'test+alias@example.com'
    """
    # Basic validation and normalization
    if not email or not email.strip():
        raise ValueError("Email address cannot be empty")

    email = email.strip().lower()

    # Validate email structure
    if '@' not in email:
        raise ValueError("Email address must contain '@' symbol")

    parts = email.split('@')
    if len(parts) != 2:
        raise ValueError("Email address must contain exactly one '@' symbol")

    local_part, domain = parts

    # Validate parts are not empty
    if not local_part or not domain:
        raise ValueError("Email address must have both local and domain parts")

    # Gmail-specific normalization
    gmail_domains = {'gmail.com', 'googlemail.com'}

    if domain in gmail_domains:
        # Remove all dots from local part
        local_part = local_part.replace('.', '')

        # Remove +tag suffix (everything after +)
        if '+' in local_part:
            local_part = local_part.split('+')[0]

        # Standardize domain to gmail.com
        domain = 'gmail.com'

    # Return normalized email
    return f"{local_part}@{domain}"
