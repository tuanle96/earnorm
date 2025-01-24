"""Notifications module for monitoring alerts."""

import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, TypedDict

from aiohttp import ClientSession
from aiosmtplib import SMTP

from earnorm.monitoring.alerts.rules import Alert

logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "monitoring@earnbase.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "monitoring@earnbase.com")


class SlackAttachmentField(TypedDict):
    """Slack attachment field structure."""

    title: str
    value: str
    short: bool


class SlackAttachment(TypedDict):
    """Slack attachment structure."""

    color: str
    title: str
    fields: List[SlackAttachmentField]
    text: Optional[str]


class SlackMessage(TypedDict):
    """Slack message structure."""

    channel: str
    attachments: List[SlackAttachment]


class NotificationSystem:
    """System for sending alert notifications.

    Examples:
        >>> notification_system = NotificationSystem()
        >>> # Add email channel
        >>> notification_system.add_email_channel(["admin@example.com"], severity_filter="critical")
        >>> # Add Slack channel
        >>> notification_system.add_slack_channel("https://hooks.slack.com/...", "#alerts", severity_filter="warning")
        >>> # Send alert
        >>> alert = Alert(name="High CPU Usage", metric="cpu_usage", value=95, threshold=90, severity="critical")
        >>> await notification_system.send_alert(alert)
    """

    def __init__(self) -> None:
        """Initialize the notification system."""
        self._notification_channels: Dict[str, List[Dict[str, Any]]] = {
            "email": [],
            "slack": [],
            "webhook": [],
        }

    def add_email_channel(
        self, recipients: List[str], severity_filter: Optional[str] = None
    ) -> None:
        """Add email notification channel.

        Args:
            recipients: List of email addresses to send notifications to
            severity_filter: Optional severity level to filter alerts by
        """
        self._notification_channels["email"].append(
            {"recipients": recipients, "severity_filter": severity_filter}
        )

    def add_slack_channel(
        self, webhook_url: str, channel: str, severity_filter: Optional[str] = None
    ) -> None:
        """Add Slack notification channel.

        Args:
            webhook_url: Slack webhook URL
            channel: Slack channel name
            severity_filter: Optional severity level to filter alerts by
        """
        self._notification_channels["slack"].append(
            {
                "webhook_url": webhook_url,
                "channel": channel,
                "severity_filter": severity_filter,
            }
        )

    def add_webhook_channel(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        severity_filter: Optional[str] = None,
    ) -> None:
        """Add webhook notification channel.

        Args:
            url: Webhook URL
            headers: Optional HTTP headers
            severity_filter: Optional severity level to filter alerts by
        """
        self._notification_channels["webhook"].append(
            {"url": url, "headers": headers or {}, "severity_filter": severity_filter}
        )

    async def send_alert(self, alert: Alert) -> None:
        """Send alert notification to all configured channels.

        Args:
            alert: Alert object containing alert details
        """
        # Send to email channels
        for channel in self._notification_channels["email"]:
            if (
                not channel["severity_filter"]
                or channel["severity_filter"] == alert.severity
            ):
                await self._send_email_alert(alert, channel["recipients"])

        # Send to Slack channels
        for channel in self._notification_channels["slack"]:
            if (
                not channel["severity_filter"]
                or channel["severity_filter"] == alert.severity
            ):
                await self._send_slack_alert(
                    alert, channel["webhook_url"], channel["channel"]
                )

        # Send to webhook channels
        for channel in self._notification_channels["webhook"]:
            if (
                not channel["severity_filter"]
                or channel["severity_filter"] == alert.severity
            ):
                await self._send_webhook_alert(
                    alert, channel["url"], channel["headers"]
                )

    async def send_resolution(self, alert: Alert) -> None:
        """Send alert resolution notification to all configured channels.

        Args:
            alert: Alert object containing alert details
        """
        # Send to email channels
        for channel in self._notification_channels["email"]:
            if (
                not channel["severity_filter"]
                or channel["severity_filter"] == alert.severity
            ):
                await self._send_email_resolution(alert, channel["recipients"])

        # Send to Slack channels
        for channel in self._notification_channels["slack"]:
            if (
                not channel["severity_filter"]
                or channel["severity_filter"] == alert.severity
            ):
                await self._send_slack_resolution(
                    alert, channel["webhook_url"], channel["channel"]
                )

        # Send to webhook channels
        for channel in self._notification_channels["webhook"]:
            if (
                not channel["severity_filter"]
                or channel["severity_filter"] == alert.severity
            ):
                await self._send_webhook_resolution(
                    alert, channel["url"], channel["headers"]
                )

    async def _send_email_alert(self, alert: Alert, recipients: List[str]) -> None:
        """Send alert via email.

        Args:
            alert: Alert object containing alert details
            recipients: List of email addresses to send to
        """
        # Create message
        msg = MIMEMultipart()
        msg["Subject"] = f"[{alert.severity.upper()}] {alert.name}"
        msg["From"] = SMTP_FROM
        msg["To"] = ", ".join(recipients)

        # Create HTML body
        html = f"""
        <h2>Alert: {alert.name}</h2>
        <p><b>Metric:</b> {alert.metric}</p>
        <p><b>Value:</b> {alert.value}</p>
        <p><b>Threshold:</b> {alert.threshold}</p>
        <p><b>Severity:</b> {alert.severity}</p>
        <p><b>Time:</b> {alert.timestamp}</p>
        """
        if alert.description:
            html += f"<p><b>Description:</b> {alert.description}</p>"

        msg.attach(MIMEText(html, "html"))

        # Send email
        try:
            smtp = SMTP(hostname=SMTP_HOST, port=SMTP_PORT, use_tls=True)
            async with smtp as server:
                await server.login(SMTP_USERNAME, SMTP_PASSWORD)
                await server.send_message(msg)
        except Exception:
            logger.exception("Failed to send email alert")

    async def _send_slack_alert(
        self, alert: Alert, webhook_url: str, channel: str
    ) -> None:
        """Send alert via Slack.

        Args:
            alert: Alert object containing alert details
            webhook_url: Slack webhook URL
            channel: Slack channel name
        """
        # Create message
        message: SlackMessage = {
            "channel": channel,
            "attachments": [
                {
                    "color": {
                        "critical": "#ff0000",
                        "warning": "#ffa500",
                        "info": "#0000ff",
                    }.get(alert.severity, "#808080"),
                    "title": f"[{alert.severity.upper()}] {alert.name}",
                    "fields": [
                        {"title": "Metric", "value": alert.metric, "short": True},
                        {"title": "Value", "value": str(alert.value), "short": True},
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True,
                        },
                        {"title": "Time", "value": str(alert.timestamp), "short": True},
                    ],
                    "text": alert.description if alert.description else None,
                }
            ],
        }

        # Send to Slack
        try:
            async with ClientSession() as session:
                async with session.post(webhook_url, json=message) as resp:
                    if resp.status != 200:
                        response_text = await resp.text()
                        logger.error(
                            "Failed to send Slack alert",
                            extra={
                                "status": resp.status,
                                "response": response_text,
                            },
                        )
        except Exception:
            logger.exception("Failed to send Slack alert")

    async def _send_webhook_alert(
        self, alert: Alert, url: str, headers: Dict[str, str]
    ) -> None:
        """Send alert via webhook.

        Args:
            alert: Alert object containing alert details
            url: Webhook URL
            headers: HTTP headers
        """
        # Create payload
        payload = {"alert": alert.to_dict(), "type": "alert"}

        # Send to webhook
        try:
            async with ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status not in (200, 201, 202):
                        response_text = await resp.text()
                        logger.error(
                            "Failed to send webhook alert",
                            extra={
                                "status": resp.status,
                                "response": response_text,
                            },
                        )
        except Exception:
            logger.exception("Failed to send webhook alert")

    async def _send_email_resolution(self, alert: Alert, recipients: List[str]) -> None:
        """Send resolution via email.

        Args:
            alert: Alert object containing alert details
            recipients: List of email addresses to send to
        """
        # Create message
        msg = MIMEMultipart()
        msg["Subject"] = f"[RESOLVED] {alert.name}"
        msg["From"] = SMTP_FROM
        msg["To"] = ", ".join(recipients)

        # Create HTML body
        html = f"""
        <h2>Alert Resolved: {alert.name}</h2>
        <p><b>Metric:</b> {alert.metric}</p>
        <p><b>Value:</b> {alert.value}</p>
        <p><b>Threshold:</b> {alert.threshold}</p>
        <p><b>Severity:</b> {alert.severity}</p>
        <p><b>Time:</b> {alert.timestamp}</p>
        """
        if alert.description:
            html += f"<p><b>Description:</b> {alert.description}</p>"

        msg.attach(MIMEText(html, "html"))

        # Send email
        try:
            smtp = SMTP(hostname=SMTP_HOST, port=SMTP_PORT, use_tls=True)
            async with smtp as server:
                await server.login(SMTP_USERNAME, SMTP_PASSWORD)
                await server.send_message(msg)
        except Exception:
            logger.exception("Failed to send email resolution")

    async def _send_slack_resolution(
        self, alert: Alert, webhook_url: str, channel: str
    ) -> None:
        """Send resolution via Slack.

        Args:
            alert: Alert object containing alert details
            webhook_url: Slack webhook URL
            channel: Slack channel name
        """
        # Create message
        message: SlackMessage = {
            "channel": channel,
            "attachments": [
                {
                    "color": "#00ff00",  # Green for resolved
                    "title": f"[RESOLVED] {alert.name}",
                    "fields": [
                        {"title": "Metric", "value": alert.metric, "short": True},
                        {"title": "Value", "value": str(alert.value), "short": True},
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True,
                        },
                        {"title": "Time", "value": str(alert.timestamp), "short": True},
                    ],
                    "text": alert.description if alert.description else None,
                }
            ],
        }

        # Send to Slack
        try:
            async with ClientSession() as session:
                async with session.post(webhook_url, json=message) as resp:
                    if resp.status != 200:
                        response_text = await resp.text()
                        logger.error(
                            "Failed to send Slack resolution",
                            extra={
                                "status": resp.status,
                                "response": response_text,
                            },
                        )
        except Exception:
            logger.exception("Failed to send Slack resolution")

    async def _send_webhook_resolution(
        self, alert: Alert, url: str, headers: Dict[str, str]
    ) -> None:
        """Send resolution via webhook.

        Args:
            alert: Alert object containing alert details
            url: Webhook URL
            headers: HTTP headers
        """
        # Create payload
        payload = {"alert": alert.to_dict(), "type": "resolution"}

        # Send to webhook
        try:
            async with ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status not in (200, 201, 202):
                        response_text = await resp.text()
                        logger.error(
                            "Failed to send webhook resolution",
                            extra={
                                "status": resp.status,
                                "response": response_text,
                            },
                        )
        except Exception:
            logger.exception("Failed to send webhook resolution")
