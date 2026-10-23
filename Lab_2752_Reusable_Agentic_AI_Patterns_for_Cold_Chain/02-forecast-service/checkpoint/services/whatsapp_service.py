"""
WhatsApp Notification Service

Sends WhatsApp messages via Twilio when credentials are configured.
Falls back to mock mode automatically when TWILIO_AUTH_TOKEN is absent —
the notification is stored in memory and a simulated message_sid is returned.
This allows the lab pipeline to run end-to-end without real Twilio credentials.

Mock mode is active when TWILIO_AUTH_TOKEN is not set (default for lab).
Real mode requires: TWILIO_AUTH_TOKEN + DEMO_PHONE_NUMBER in forecast-backend/.env
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# In-memory store for mock notifications (cleared on restart)
_mock_notifications: list = []


class WhatsAppService:
    """Service for sending WhatsApp notifications via Twilio, with mock fallback."""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.from_number = os.getenv('TWILIO_FROM_NUMBER', 'whatsapp:+14155238886')
        self.demo_phone = os.getenv('DEMO_PHONE_NUMBER', '+10000000000')

        # Mock mode when no auth token — no crash, lab continues normally
        self.mock_mode = not bool(self.auth_token)

        if self.mock_mode:
            logger.info("WhatsApp service running in MOCK mode "
                        "(TWILIO_AUTH_TOKEN not set — notifications simulated, not sent)")
        else:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("WhatsApp service running in LIVE mode via Twilio")

    def format_decision_message(
        self,
        truck_id: str,
        decision: Dict,
        driver_name: str = "Driver"
    ) -> str:
        """Format decision agent output into a driver-friendly WhatsApp message."""
        action = decision.get('action', 'UNKNOWN')
        urgency = decision.get('urgency', 'MEDIUM')
        facility = decision.get('selected_facility', {})
        destination = facility.get('name', 'Unknown destination')
        route = decision.get('selected_route', {})
        eta_minutes = route.get('duration_minutes', 0)
        risk_factors = decision.get('risk_factors', {})
        temperature = risk_factors.get('temperature', {}).get('value', 'N/A')
        risk_score = decision.get('risk_score', 0)
        reasoning = decision.get('reasoning', [])
        reason = reasoning[0] if reasoning else "See dashboard for details"

        urgency_emoji = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': 'ℹ️', 'LOW': '✅'}.get(urgency, 'ℹ️')

        return (
            f"{urgency_emoji} FleetOPTX Alert - {truck_id}\n\n"
            f"Driver: {driver_name}\n\n"
            f"**{action}**\n"
            f"Urgency: {urgency}\n\n"
            f"📍 {destination}\n"
            f"⏱️ ETA: {eta_minutes} min\n\n"
            f"⚠️ Reason: {reason}\n"
            f"🌡️ Temperature: {temperature}°C\n"
            f"📊 Risk: {risk_score}/100\n\n"
            f"Reply \"OK\" to acknowledge.\n\n"
            f"- FleetOPTX Command Center"
        )

    def send_notification(
        self,
        truck_id: str,
        decision: Dict,
        driver_name: str = "Driver",
        phone_number: Optional[str] = None
    ) -> Dict:
        """
        Send (or simulate) a WhatsApp notification.

        In mock mode: stores the notification in memory and returns a simulated SID.
        In live mode: sends via Twilio to DEMO_PHONE_NUMBER (or phone_number override).
        """
        message_body = self.format_decision_message(truck_id, decision, driver_name)
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.mock_mode:
            mock_sid = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
            to_number = phone_number or self.demo_phone
            record = {
                'status': 'SENT',
                'message_sid': mock_sid,
                'timestamp': timestamp,
                'truck_id': truck_id,
                'to': to_number,
                'body': message_body,
                'demo_mode': True,
                'mock': True,
            }
            _mock_notifications.append(record)
            logger.info("Mock WhatsApp notification stored for %s — SID %s", truck_id, mock_sid)
            return record

        # Live Twilio path
        try:
            from twilio.base.exceptions import TwilioRestException
            to_number = phone_number or self.demo_phone
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            message = self.client.messages.create(
                from_=self.from_number,
                to=to_number,
                body=message_body
            )
            return {
                'status': 'SENT',
                'message_sid': message.sid,
                'timestamp': timestamp,
                'truck_id': truck_id,
                'to': to_number,
                'demo_mode': True,
                'mock': False,
            }
        except Exception as e:
            logger.error("Twilio send failed for %s: %s", truck_id, e)
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': timestamp,
                'truck_id': truck_id,
                'mock': False,
            }

    def check_delivery_status(self, message_sid: str) -> Dict:
        """Return delivery status. Mock SIDs return 'delivered' immediately."""
        if message_sid.startswith('MOCK-'):
            return {'status': 'delivered', 'mock': True, 'message_sid': message_sid}
        if self.mock_mode:
            return {'status': 'delivered', 'mock': True, 'message_sid': message_sid}
        try:
            from twilio.base.exceptions import TwilioRestException
            message = self.client.messages(message_sid).fetch()
            return {
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'date_sent': message.date_sent.isoformat() if message.date_sent else None,
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    def get_mock_notifications(self) -> list:
        """Return all mock notifications stored this session (mock mode only)."""
        return list(_mock_notifications)


# Singleton
_whatsapp_service: Optional[WhatsAppService] = None

def get_whatsapp_service() -> WhatsAppService:
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service

# Made with Bob
