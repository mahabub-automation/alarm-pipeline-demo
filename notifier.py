"""
Notification module.
Reusable across all automation tools.
"""

import requests
import logging

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends messages and files to a Telegram chat."""

    def __init__(self, token, chat_id):
        if not token or not chat_id:
            raise ValueError("Telegram token and chat_id are required.")
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, text, parse_mode="HTML"):
        """Send a text message."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            logger.info("Message sent successfully.")
            return True
        except requests.exceptions.RequestException as error:
            logger.error(f"Failed to send message: {error}")
            return False

    def send_document(self, file_path, caption=""):
        """Send a file such as Excel, PDF or an image."""
        url = f"{self.base_url}/sendDocument"
        try:
            with open(file_path, "rb") as file_handle:
                files = {"document": file_handle}
                data = {"chat_id": self.chat_id, "caption": caption}
                response = requests.post(url, data=data, files=files, timeout=60)
                response.raise_for_status()
            logger.info(f"Document sent: {file_path}")
            return True
        except Exception as error:
            logger.error(f"Failed to send document: {error}")
            return False

    def test_connection(self):
        """Verify that the bot token is valid."""
        url = f"{self.base_url}/getMe"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            bot_name = response.json()["result"]["username"]
            logger.info(f"Connected to bot: @{bot_name}")
            return True
        except Exception as error:
            logger.error(f"Connection test failed: {error}")
            return False