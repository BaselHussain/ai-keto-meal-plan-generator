"""
Unit tests for email normalization utilities.

This module contains comprehensive tests for the normalize_email() function,
covering Gmail-specific normalization rules, edge cases, and error conditions.

Tests verify:
- Gmail dot removal
- Gmail plus-tag removal
- Case insensitivity
- Googlemail to Gmail conversion
- Combined Gmail features
- Non-Gmail domain preservation
- Input validation and error handling
"""

import pytest

from src.lib.email_utils import normalize_email


class TestNormalizeEmail:
    """Test suite for email normalization function."""

    # Gmail-specific normalization tests

    def test_gmail_dot_removal(self):
        """Gmail dots are removed from local part."""
        result = normalize_email("user.name@gmail.com")
        assert result == "username@gmail.com"

    def test_gmail_plus_tag_removal(self):
        """Gmail plus-tags are removed from local part."""
        result = normalize_email("user+tag@gmail.com")
        assert result == "user@gmail.com"

    def test_case_insensitivity(self):
        """Email is normalized to lowercase."""
        result = normalize_email("User@Gmail.COM")
        assert result == "user@gmail.com"

    def test_googlemail_to_gmail_conversion(self):
        """Googlemail.com domain is converted to gmail.com."""
        result = normalize_email("user@googlemail.com")
        assert result == "user@gmail.com"

    def test_combined_gmail_features(self):
        """All Gmail normalization rules work together."""
        result = normalize_email("User.Name+Tag@GoogleMail.com")
        assert result == "username@gmail.com"

    def test_gmail_multiple_dots(self):
        """Multiple dots in Gmail local part are all removed."""
        result = normalize_email("user.name.test@gmail.com")
        assert result == "usernametest@gmail.com"

    def test_gmail_plus_tag_with_dots(self):
        """Dots and plus-tags work correctly together."""
        result = normalize_email("user.name+alias@gmail.com")
        assert result == "username@gmail.com"

    # Non-Gmail domain tests

    def test_non_gmail_plus_tag_preserved(self):
        """Plus-tags are preserved for non-Gmail domains."""
        result = normalize_email("test+tag@example.com")
        assert result == "test+tag@example.com"

    def test_non_gmail_dots_preserved(self):
        """Dots are preserved for non-Gmail domains."""
        result = normalize_email("user.name@example.com")
        assert result == "user.name@example.com"

    def test_non_gmail_case_normalization(self):
        """Non-Gmail domains are lowercased but structure preserved."""
        result = normalize_email("Test.Name+Alias@Example.COM")
        assert result == "test.name+alias@example.com"

    # Whitespace handling

    def test_whitespace_trimming(self):
        """Leading and trailing whitespace is removed."""
        result = normalize_email("  user@gmail.com  ")
        assert result == "user@gmail.com"

    def test_whitespace_with_normalization(self):
        """Whitespace trimming works with Gmail normalization."""
        result = normalize_email("  User.Name+Tag@Gmail.com  ")
        assert result == "username@gmail.com"

    # Error cases

    def test_empty_email_raises_error(self):
        """Empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email address cannot be empty"):
            normalize_email("")

    def test_whitespace_only_email_raises_error(self):
        """Whitespace-only email raises ValueError."""
        with pytest.raises(ValueError, match="Email address cannot be empty"):
            normalize_email("   ")

    def test_missing_at_symbol_raises_error(self):
        """Email without @ symbol raises ValueError."""
        with pytest.raises(ValueError, match="Email address must contain '@' symbol"):
            normalize_email("notanemail")

    def test_multiple_at_symbols_raises_error(self):
        """Email with multiple @ symbols raises ValueError."""
        with pytest.raises(ValueError, match="Email address must contain exactly one '@' symbol"):
            normalize_email("user@@example.com")

    def test_multiple_at_symbols_complex_raises_error(self):
        """Email with @ in both local and domain raises ValueError."""
        with pytest.raises(ValueError, match="Email address must contain exactly one '@' symbol"):
            normalize_email("user@domain@example.com")

    def test_missing_local_part_raises_error(self):
        """Email without local part raises ValueError."""
        with pytest.raises(ValueError, match="Email address must have both local and domain parts"):
            normalize_email("@example.com")

    def test_missing_domain_raises_error(self):
        """Email without domain raises ValueError."""
        with pytest.raises(ValueError, match="Email address must have both local and domain parts"):
            normalize_email("user@")

    # Edge cases

    def test_single_character_local_part(self):
        """Single character local part is handled correctly."""
        result = normalize_email("a@gmail.com")
        assert result == "a@gmail.com"

    def test_gmail_plus_at_end(self):
        """Gmail plus-tag at end with no suffix is handled correctly."""
        result = normalize_email("user+@gmail.com")
        assert result == "user@gmail.com"

    def test_complex_non_gmail_domain(self):
        """Complex non-Gmail domain is preserved."""
        result = normalize_email("user.name@mail.example.co.uk")
        assert result == "user.name@mail.example.co.uk"

    def test_numeric_local_part(self):
        """Numeric local part is handled correctly."""
        result = normalize_email("12345@gmail.com")
        assert result == "12345@gmail.com"

    def test_gmail_hyphen_preserved(self):
        """Hyphens in Gmail local part are preserved."""
        result = normalize_email("user-name@gmail.com")
        assert result == "user-name@gmail.com"

    def test_gmail_underscore_preserved(self):
        """Underscores in Gmail local part are preserved."""
        result = normalize_email("user_name@gmail.com")
        assert result == "user_name@gmail.com"

    # Idempotency tests

    def test_normalization_is_idempotent(self):
        """Normalizing an already normalized email returns the same result."""
        email = "username@gmail.com"
        result1 = normalize_email(email)
        result2 = normalize_email(result1)
        assert result1 == result2

    def test_complex_normalization_idempotent(self):
        """Complex normalization is idempotent."""
        email = "User.Name+Tag@GoogleMail.com"
        result1 = normalize_email(email)
        result2 = normalize_email(result1)
        assert result1 == result2
        assert result1 == "username@gmail.com"
