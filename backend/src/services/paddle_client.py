"""
Paddle API Client for Refund Processing
Handles API communication with Paddle for processing refunds.

Features:
- Payment method compatibility checking
- Refund processing via Paddle API
- Error handling and validation
- Support for different payment methods

File: backend/src/services/paddle_client.py
"""
import logging
import requests
from typing import Dict, Any, Optional
from enum import Enum

from src.lib.env import settings

logger = logging.getLogger(__name__)


class RefundMethod(Enum):
    """Payment methods available for refund processing."""
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    PAYPAL = "PayPal"
    VENMO = "Venmo"
    BANK_TRANSFER = "Bank Transfer"
    UNKNOWN = "Unknown"


class PaddleClient:
    """
    Client for interacting with the Paddle API for refund operations.
    """

    def __init__(self):
        self.api_key = settings.PADDLE_API_KEY
        self.base_url = "https://vendors.paddle.com/api/2.0"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def process_sla_refund(self, refund_data: Dict[str, Any]) -> bool:
        """
        Process a refund for SLA violation.

        Args:
            refund_data: Dictionary containing refund information:
                - payment_id: The Paddle payment ID to refund
                - amount: The amount to refund
                - reason: The reason for the refund
                - email: The user's email

        Returns:
            bool: True if refund was processed successfully, False otherwise
        """
        logger.info(f"Processing SLA refund for payment {refund_data['payment_id']}")

        try:
            # First verify the payment method is compatible with refunds
            payment_compatible = await self.check_payment_method_compatibility(refund_data['payment_id'])

            if not payment_compatible:
                logger.warning(f"Payment method for {refund_data['payment_id']} may not support refunds")

            # Prepare refund request data
            payload = {
                "payment_id": refund_data["payment_id"],
                "amount": refund_data["amount"],
                "reason": refund_data["reason"]
            }

            # Handle Paddle refund API call
            response = requests.post(
                f"{self.base_url}/payments/refund",
                headers=self.headers,
                json=payload
            )

            logger.info(f"Paddle refund API response: {response.status_code}, {response.text}")

            if response.status_code == 200:
                refund_response = response.json()

                # Check if refund was successful
                if refund_response.get("success", False):
                    logger.info(f"Successfully refunded payment {refund_data['payment_id']}")
                    return True
                else:
                    logger.error(f"Paddle refund failed: {refund_response}")
                    return False
            else:
                logger.error(f"Paddle refund API error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during Paddle refund: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Paddle refund: {e}")
            return False

    async def check_payment_method_compatibility(self, payment_id: str) -> bool:
        """
        Check if the payment method used for this transaction is compatible with refunds.

        Args:
            payment_id: The Paddle payment ID to check

        Returns:
            bool: True if payment method supports refunds, False otherwise
        """
        try:
            # Get payment transaction details from Paddle to check payment method
            response = requests.get(
                f"{self.base_url}/payment/{payment_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                payment_info = response.json()

                # Extract payment method from payment data
                payment_method = payment_info.get("payment_method", "unknown").lower()

                # Based on known Paddle payment methods that support refunds
                refund_compatible = [
                    "credit_card", "cc", "card", "visa", "mastercard",  # Credit/Debit cards
                    "paypal",  # PayPal
                    "bank_transfer",  # Bank transfers (varies by region)
                    "sepa", "ach"  # Direct bank transfers in some regions
                ]

                # Return True if the payment method is compatible with refunds
                is_compatible = payment_method in refund_compatible

                logger.info(f"Payment method for {payment_id}: {payment_method}, compatible: {is_compatible}")

                return is_compatible
            else:
                logger.error(f"Error getting payment info from Paddle: {response.status_code} - {response.text}")
                # If we can't verify, assume it's compatible to not prevent refunds if API is temporarily down
                return True

        except Exception as e:
            logger.error(f"Error checking payment method compatibility for {payment_id}: {e}")
            # If we can't verify, assume it's compatible to not prevent refunds
            return True

    async def get_payment_details(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment details from Paddle API.

        Args:
            payment_id: The Paddle payment ID to retrieve details for

        Returns:
            Dict containing payment details or None if error
        """
        try:
            response = requests.get(
                f"{self.base_url}/payment/{payment_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("payment", result)  # Paddle API might wrap response
            else:
                logger.error(f"Failed to get payment details: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving payment details for {payment_id}: {e}")
            return None

    async def create_transaction_refund(self, payment_id: str, amount: float, reason: str) -> bool:
        """
        Alternative method to process refund using transaction ID.

        Args:
            payment_id: The Paddle payment ID to refund
            amount: The amount to refund
            reason: The reason for refund

        Returns:
            bool: True if refund was created successfully, False otherwise
        """
        try:
            # Check if the payment method allows refund
            is_compatible = await self.check_payment_method_compatibility(payment_id)
            if not is_compatible:
                logger.warning(f"Payment {payment_id} has incompatible payment method for refund")

            # Prepare refund data
            refund_payload = {
                "payment_id": payment_id,
                "amount": amount,
                "reason": reason,
                "refund_type": "full"  # Default to full refund, can be partial
            }

            response = requests.post(
                f"{self.base_url}/payment/refund",
                headers=self.headers,
                json=refund_payload
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    logger.info(f"Created refund transaction for payment {payment_id}")
                    return True
                else:
                    logger.error(f"Failed to create refund transaction: {result}")
                    return False
            else:
                error_msg = f"API call failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return False

        except Exception as e:
            logger.error(f"Error creating transaction refund: {e}")
            return False