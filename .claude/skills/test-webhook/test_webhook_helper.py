#!/usr/bin/env python3
"""
Helper script to test Paddle webhooks for the keto meal plan project.
Simulates webhook events and monitors the full pipeline execution.
"""

import argparse
import hmac
import hashlib
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any
import requests

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend', 'src'))

def generate_payment_id(event_type: str) -> str:
    """Generate a test payment ID."""
    timestamp = int(time.time())
    return f"pay_test_{event_type}_{timestamp}"

def create_webhook_payload(event_type: str, payment_id: str) -> Dict[str, Any]:
    """Create webhook payload based on event type."""
    current_time = datetime.utcnow().isoformat() + "Z"

    if event_type == "payment.succeeded":
        return {
            "event_type": "payment.succeeded",
            "payment_id": payment_id,
            "customer_email": "test@example.com",
            "amount": 29.99,
            "currency": "USD",
            "payment_method": "card",
            "created_at": current_time
        }
    elif event_type == "payment.chargeback":
        return {
            "event_type": "payment.chargeback",
            "payment_id": payment_id,
            "customer_email": "test@example.com",
            "amount": 29.99,
            "reason": "fraudulent",
            "created_at": current_time
        }
    elif event_type == "payment.refunded":
        return {
            "event_type": "payment.refunded",
            "payment_id": payment_id,
            "refund_amount": 29.99,
            "refund_reason": "customer_request",
            "created_at": current_time
        }
    else:
        raise ValueError(f"Unknown event type: {event_type}")

def calculate_signature(payload: str, timestamp: int, webhook_secret: str) -> str:
    """Calculate HMAC-SHA256 signature for webhook."""
    message = f"{timestamp}{payload}"
    signature = hmac.new(
        webhook_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def create_test_quiz(email: str = "test@example.com") -> str:
    """Create a test quiz response in the database."""
    try:
        from models.quiz_response import QuizResponse
        from lib.database import SessionLocal

        quiz = QuizResponse(
            email=email,
            quiz_data={
                'step_1': 'female',
                'step_2': 'moderately_active',
                'step_3': ['chicken', 'turkey'],
                'step_4': ['salmon', 'tuna'],
                'step_20': {
                    'age': 30,
                    'weight_kg': 70,
                    'height_cm': 165,
                    'goal': 'weight_loss'
                }
            },
            calorie_target=1650
        )

        db = SessionLocal()
        db.add(quiz)
        db.commit()
        quiz_id = str(quiz.id)
        db.close()

        print(f"✅ Test quiz created: {quiz_id}")
        return quiz_id
    except Exception as e:
        print(f"⚠️ Could not create test quiz: {e}")
        print("   Backend models may not be initialized yet")
        return None

def send_webhook(
    backend_url: str,
    payload: Dict[str, Any],
    webhook_secret: str,
    invalid_signature: bool = False,
    expired_timestamp: bool = False
) -> requests.Response:
    """Send webhook request to backend."""

    # Generate timestamp
    if expired_timestamp:
        timestamp = int(time.time()) - 400  # 6+ minutes ago
    else:
        timestamp = int(time.time())

    # Convert payload to JSON string
    payload_str = json.dumps(payload)

    # Calculate signature
    if invalid_signature:
        signature = "invalid_signature_for_testing"
    else:
        signature = calculate_signature(payload_str, timestamp, webhook_secret)

    # Send request
    headers = {
        "Content-Type": "application/json",
        "Paddle-Signature": signature,
        "Paddle-Timestamp": str(timestamp)
    }

    print(f"\n📤 Sending webhook to {backend_url}/webhooks/paddle")
    print(f"   Event: {payload['event_type']}")
    print(f"   Payment ID: {payload['payment_id']}")
    print(f"   Timestamp: {timestamp}")
    print(f"   Signature: {signature[:32]}...")

    response = requests.post(
        f"{backend_url}/webhooks/paddle",
        headers=headers,
        json=payload,
        timeout=120  # 2 minute timeout for full pipeline
    )

    return response

def check_meal_plan(payment_id: str) -> Dict[str, Any]:
    """Check if meal plan was created in database."""
    try:
        from models.meal_plan import MealPlan
        from lib.database import SessionLocal

        db = SessionLocal()
        plan = db.query(MealPlan).filter_by(payment_id=payment_id).first()
        db.close()

        if plan:
            return {
                "found": True,
                "status": plan.status,
                "pdf_url": plan.pdf_url,
                "email_sent_at": plan.email_sent_at.isoformat() if plan.email_sent_at else None,
                "created_at": plan.created_at.isoformat()
            }
        else:
            return {"found": False}
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Test Paddle webhooks")
    parser.add_argument(
        "--event",
        default="payment.succeeded",
        choices=["payment.succeeded", "payment.chargeback", "payment.refunded"],
        help="Webhook event type"
    )
    parser.add_argument("--payment-id", help="Custom payment ID")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--webhook-secret", help="Paddle webhook secret (or set PADDLE_WEBHOOK_SECRET env)")
    parser.add_argument("--missing-quiz", action="store_true", help="Test missing quiz scenario")
    parser.add_argument("--duplicate", action="store_true", help="Send webhook twice (test idempotency)")
    parser.add_argument("--invalid-signature", action="store_true", help="Send invalid signature")
    parser.add_argument("--expired-timestamp", action="store_true", help="Send expired timestamp")

    args = parser.parse_args()

    # Get webhook secret
    webhook_secret = args.webhook_secret or os.getenv("PADDLE_WEBHOOK_SECRET")
    if not webhook_secret:
        print("❌ Error: PADDLE_WEBHOOK_SECRET not set")
        print("   Set env var or use --webhook-secret")
        sys.exit(1)

    # Check backend health
    try:
        response = requests.get(f"{args.backend_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Backend not healthy: {response.status_code}")
            sys.exit(1)
        print(f"✅ Backend is running at {args.backend_url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not accessible: {e}")
        print(f"   Start backend with: cd backend && uvicorn src.main:app --reload")
        sys.exit(1)

    # Generate payment ID
    payment_id = args.payment_id or generate_payment_id(args.event.split('.')[1])

    # Create test quiz for payment success events (unless testing missing quiz)
    if args.event == "payment.succeeded" and not args.missing_quiz:
        create_test_quiz("test@example.com")
        print("   Waiting 1s for database commit...")
        time.sleep(1)

    # Create payload
    payload = create_webhook_payload(args.event, payment_id)

    # Record start time
    start_time = time.time()

    # Send webhook
    try:
        response = send_webhook(
            args.backend_url,
            payload,
            webhook_secret,
            invalid_signature=args.invalid_signature,
            expired_timestamp=args.expired_timestamp
        )

        elapsed = time.time() - start_time

        print(f"\n📥 Webhook Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Time: {elapsed:.2f}s")

        if response.status_code == 200:
            print("   ✅ Webhook accepted")

            # Check if meal plan was created (for payment.succeeded)
            if args.event == "payment.succeeded":
                print("\n🔍 Checking database for meal plan...")
                time.sleep(2)  # Wait for async processing

                result = check_meal_plan(payment_id)
                if result.get("found"):
                    print(f"   ✅ Meal Plan Created")
                    print(f"      Status: {result['status']}")
                    print(f"      PDF URL: {result['pdf_url']}")
                    print(f"      Email Sent: {result['email_sent_at']}")
                elif result.get("error"):
                    print(f"   ⚠️ Database check error: {result['error']}")
                else:
                    print(f"   ⏳ Meal plan not yet created (async processing)")
        elif response.status_code == 401:
            print("   ❌ Webhook rejected (signature/timestamp validation failed)")
        else:
            print(f"   ❌ Webhook failed: {response.text}")

        # Test duplicate if requested
        if args.duplicate and response.status_code == 200:
            print("\n🔄 Testing idempotency (sending duplicate webhook)...")
            time.sleep(1)

            response2 = send_webhook(args.backend_url, payload, webhook_secret)

            if response2.status_code == 200:
                print("   ✅ Duplicate webhook handled correctly (returned 200)")
                print("   Should not have reprocessed")
            else:
                print(f"   ⚠️ Unexpected response: {response2.status_code}")

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"\n⏱️ Webhook timeout after {elapsed:.1f}s")
        print("   This may be normal for full pipeline execution")
        print("   Check backend logs and database for results")
    except Exception as e:
        print(f"\n❌ Error sending webhook: {e}")
        sys.exit(1)

    print("\n" + "="*50)
    print("✅ Webhook test completed")

if __name__ == "__main__":
    main()
