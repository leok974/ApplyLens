"""
Slack integration for incident coordination and notifications.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime
import httpx
from pydantic import BaseModel


class SlackMessage(BaseModel):
    """Slack message structure."""
    text: str
    channel: Optional[str] = None
    blocks: Optional[List[Dict]] = None
    thread_ts: Optional[str] = None


class SlackClient:
    """Client for Slack Web API."""
    
    API_BASE_URL = "https://slack.com/api"
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Slack client.
        
        Args:
            bot_token: Slack bot token (xoxb-...).
                       If not provided, reads from SLACK_BOT_TOKEN env var.
        """
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        
        if not self.bot_token:
            raise ValueError("Slack bot token not provided")
        
        self.headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }
    
    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict:
        """
        Post a message to a Slack channel.
        
        Args:
            channel: Channel ID or name (e.g., "#incidents")
            text: Message text (fallback)
            blocks: Block Kit formatted message
            thread_ts: Thread timestamp to reply in thread
        
        Returns:
            Response from Slack API with ts (timestamp)
        """
        payload = {
            "channel": channel,
            "text": text,
        }
        
        if blocks:
            payload["blocks"] = blocks
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE_URL}/chat.postMessage",
                headers=self.headers,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                raise RuntimeError(f"Slack API error: {result.get('error')}")
            
            return result
    
    async def create_channel(
        self,
        name: str,
        is_private: bool = False,
    ) -> str:
        """
        Create a new Slack channel.
        
        Args:
            name: Channel name (lowercase, no spaces)
            is_private: Whether to create a private channel
        
        Returns:
            Channel ID
        """
        endpoint = "conversations.create"
        
        payload = {
            "name": name,
            "is_private": is_private,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE_URL}/{endpoint}",
                headers=self.headers,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                raise RuntimeError(f"Slack API error: {result.get('error')}")
            
            return result["channel"]["id"]
    
    async def invite_to_channel(self, channel_id: str, user_ids: List[str]) -> Dict:
        """
        Invite users to a channel.
        
        Args:
            channel_id: Channel ID
            user_ids: List of user IDs to invite
        
        Returns:
            Response from Slack API
        """
        payload = {
            "channel": channel_id,
            "users": ",".join(user_ids),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE_URL}/conversations.invite",
                headers=self.headers,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                raise RuntimeError(f"Slack API error: {result.get('error')}")
            
            return result
    
    async def set_channel_topic(self, channel_id: str, topic: str) -> Dict:
        """Set channel topic."""
        payload = {
            "channel": channel_id,
            "topic": topic,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE_URL}/conversations.setTopic",
                headers=self.headers,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                raise RuntimeError(f"Slack API error: {result.get('error')}")
            
            return result


class SlackIncidentChannel:
    """
    Manages Slack incident coordination channels.
    
    Creates dedicated channels for incidents with:
    - Incident details pinned
    - Timeline updates
    - Command structure
    """
    
    def __init__(self, slack_client: Optional[SlackClient] = None):
        self.client = slack_client or SlackClient()
        self.incidents_channel = os.getenv("SLACK_INCIDENTS_CHANNEL", "#incidents")
    
    async def create_incident_channel(
        self,
        incident_id: str,
        title: str,
        severity: str,
        commander: str,
    ) -> str:
        """
        Create a dedicated Slack channel for incident coordination.
        
        Args:
            incident_id: Internal incident ID
            title: Incident title
            severity: SEV1, SEV2, etc.
            commander: Incident commander email
        
        Returns:
            Channel ID
        """
        # Generate channel name (lowercase, replace spaces)
        channel_name = f"inc-{incident_id.lower()}"
        
        # Create channel
        channel_id = await self.client.create_channel(name=channel_name, is_private=False)
        
        # Set topic
        topic = f"{severity} - {title} | Commander: {commander}"
        await self.client.set_channel_topic(channel_id, topic)
        
        # Post initial message with incident details
        await self._post_incident_details(channel_id, incident_id, title, severity, commander)
        
        # Announce in main incidents channel
        await self._announce_incident(incident_id, channel_name, severity)
        
        return channel_id
    
    async def post_timeline_update(
        self,
        channel_id: str,
        incident_id: str,
        update: str,
        user: str,
    ) -> str:
        """
        Post a timeline update to the incident channel.
        
        Args:
            channel_id: Incident channel ID
            incident_id: Internal incident ID
            update: Update text
            user: User making the update
        
        Returns:
            Message timestamp
        """
        timestamp = datetime.utcnow().strftime("%H:%M:%S UTC")
        
        text = f"**[{timestamp}]** {update} - _{user}_"
        
        result = await self.client.post_message(
            channel=channel_id,
            text=text,
        )
        
        return result["ts"]
    
    async def post_status_change(
        self,
        channel_id: str,
        incident_id: str,
        old_status: str,
        new_status: str,
        user: str,
    ) -> str:
        """Post status change notification."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":rotating_light: *Status Change*\n{old_status.upper()} → {new_status.upper()}\nBy: {user}",
                },
            },
        ]
        
        result = await self.client.post_message(
            channel=channel_id,
            text=f"Status changed: {old_status} → {new_status}",
            blocks=blocks,
        )
        
        return result["ts"]
    
    async def post_resolution(
        self,
        channel_id: str,
        incident_id: str,
        resolution: str,
        mttr_minutes: float,
        user: str,
    ) -> str:
        """Post incident resolution."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":white_check_mark: *Incident Resolved*\n\n**Resolution:** {resolution}\n**MTTR:** {mttr_minutes:.1f} minutes\n**Resolved by:** {user}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Next steps:\n• Complete postmortem within 48 hours\n• Update runbooks if needed\n• Archive this channel after postmortem",
                },
            },
        ]
        
        result = await self.client.post_message(
            channel=channel_id,
            text=f"Incident resolved by {user}",
            blocks=blocks,
        )
        
        return result["ts"]
    
    async def _post_incident_details(
        self,
        channel_id: str,
        incident_id: str,
        title: str,
        severity: str,
        commander: str,
    ):
        """Post initial incident details (pinned message)."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity}: {title}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Incident ID:*\n{incident_id}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Commander:*\n{commander}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Started:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Commands:*\n• `/incident status` - Update status\n• `/incident timeline` - View timeline\n• `/incident resolve` - Resolve incident",
                },
            },
        ]
        
        await self.client.post_message(
            channel=channel_id,
            text=f"Incident {incident_id}: {title}",
            blocks=blocks,
        )
    
    async def _announce_incident(self, incident_id: str, channel_name: str, severity: str):
        """Announce new incident in main channel."""
        text = f":rotating_light: New {severity} incident: #{channel_name}"
        
        await self.client.post_message(
            channel=self.incidents_channel,
            text=text,
        )


# Global instance
_slack_incident_channel = None


def get_slack_incident_channel() -> SlackIncidentChannel:
    """Get global Slack incident channel manager."""
    global _slack_incident_channel
    if _slack_incident_channel is None:
        _slack_incident_channel = SlackIncidentChannel()
    return _slack_incident_channel
