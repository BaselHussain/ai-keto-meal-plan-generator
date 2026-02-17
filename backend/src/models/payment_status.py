"""
Payment Status Enum
Defines the valid statuses for payment transactions.

File: backend/src/models/payment_status.py
"""
from enum import Enum


class PaymentStatus(str, Enum):
    """
    Payment transaction status enum.

    Values:
        SUCCEEDED: Payment completed successfully
        REFUNDED: Payment refunded by merchant or customer
        CHARGEBACK: Customer disputed payment with bank
    """
    SUCCEEDED = "succeeded"
    REFUNDED = "refunded"
    CHARGEBACK = "chargeback"


# For backward compatibility where string values are expected
PAYMENT_STATUS_CHOICES = [
    PaymentStatus.SUCCEEDED,
    PaymentStatus.REFUNDED,
    PaymentStatus.CHARGEBACK,
]