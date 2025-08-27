import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# Configure logging
log_path = Path().absolute() / "monitor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class NotificationManager:
    """Handles multiple notification methods"""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def send_email(self, subject: str, body: str):
        """Send email using temporary/disposable email services"""
        try:
            # Using Mailgun (free tier: 5,000 emails/month)
            if "mailgun" in self.config:
                return self._send_mailgun(subject, body)

            # Using SendGrid (free tier: 100 emails/day)
            elif "sendgrid" in self.config:
                return self._send_sendgrid(subject, body)

        except Exception as e:
            logger.error(f"Error sending email: {e}")

    def _send_mailgun(self, subject: str, body: str):
        """Send via Mailgun API"""
        mailgun_config = self.config["mailgun"]

        response = requests.post(
            f"https://api.mailgun.net/v3/{mailgun_config['domain']}/messages",
            auth=("api", mailgun_config["api_key"]),
            data={
                "from": f"Website Monitor <mailgun@{mailgun_config['domain']}>",
                "to": [mailgun_config["to_email"]],
                "subject": subject,
                "text": body,
            },
        )

        if response.status_code == 200:
            logger.info("Mailgun email sent successfully")
        else:
            logger.error(f"Mailgun error: {response.text}")

    def _send_sendgrid(self, subject: str, body: str):
        """Send via SendGrid API"""
        sendgrid_config = self.config["sendgrid"]

        headers = {
            "Authorization": f"Bearer {sendgrid_config['api_key']}",
            "Content-Type": "application/json",
        }

        data = {
            "personalizations": [{"to": [{"email": sendgrid_config["to_email"]}]}],
            "from": {"email": sendgrid_config["from_email"]},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }

        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send", headers=headers, json=data
        )

        if response.status_code == 202:
            logger.info("SendGrid email sent successfully")
        else:
            logger.error(f"SendGrid error: {response.text}")

    def send_discord(self, message: str):
        """Send Discord notification via webhook"""
        try:
            if "discord" in self.config:
                discord_config = self.config["discord"]

                data = {
                    "content": message,
                    "username": "Website Monitor",
                    "embeds": [
                        {
                            "title": "🚨 Website Update Detected",
                            "description": message,
                            "color": 0xFF0000,  # Red color
                            "timestamp": datetime.now().isoformat(),
                        }
                    ],
                }

                response = requests.post(discord_config["webhook_url"], json=data)

                if response.status_code == 204:
                    logger.info("Discord notification sent successfully")
                else:
                    logger.error(f"Discord error: {response.text}")

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")

    def send_telegram(self, message: str):
        """Send Telegram notification"""
        try:
            if "telegram" in self.config:
                telegram_config = self.config["telegram"]

                url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"

                data = {
                    "chat_id": telegram_config["chat_id"],
                    "text": f"🚨 *Website Update Detected*\n\n{message}",
                    "parse_mode": "Markdown",
                }

                response = requests.post(url, data=data)

                if response.status_code == 200:
                    logger.info("Telegram notification sent successfully")
                else:
                    logger.error(f"Telegram error: {response.text}")

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    def send_all_notifications(self, subject: str, message: str):
        """Send notifications via all configured methods"""
        # Email notifications
        if any(key in self.config for key in ["mailgun", "sendgrid"]):
            self.send_email(subject, message)

        # Chat/messaging notifications
        if "discord" in self.config:
            self.send_discord(message)

        if "telegram" in self.config:
            self.send_telegram(message)


class WebsiteMonitor:
    def __init__(self, config_file: str = "configs/basic.json"):
        # Use pathlib for path handling
        self.base_dir = Path().absolute()
        self.config = self.load_config(config_file)
        self.cache_file = self.base_dir / "content_cache.json"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                "Safari/537.36"
            }
        )
        self.notification_manager = NotificationManager(
            self.config.get("notifications", {})
        )

    def load_config(self, config_file: str) -> dict[str, Any]:  # noqa: C901
        """Load configuration from JSON file or environment variables"""
        default_config = {
            "url": "",
            "check_interval_minutes": 4,
            "target_text_keywords": [
                "Chers parents",
                "école de natation",
                "rentrée sportive",
            ],
            "min_text_length": 50,
            "notifications": {},
        }

        # Convert to Path object and resolve relative to base directory
        config_path = Path(config_file)
        if not config_path.is_absolute():
            # First check if it's in the package directory
            package_config = Path(__file__).parent.parent.parent / config_file
            if package_config.exists():
                config_path = package_config
            else:
                # Fall back to current working directory
                config_path = self.base_dir / config_file

        logger.info(f"Loading config from: {config_path}")

        # Load from file
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    file_config = json.load(f)
                default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")

        # Override with environment variables
        env_url = os.getenv("URL")
        if env_url:
            default_config["url"] = env_url

        # Load notification configs from environment
        notification_config = {}

        # Discord
        discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if discord_webhook:
            notification_config["discord"] = {"webhook_url": discord_webhook}

        # Telegram
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if telegram_bot_token and telegram_chat_id:
            notification_config["telegram"] = {
                "bot_token": telegram_bot_token,
                "chat_id": telegram_chat_id,
            }

        # SendGrid
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        sendgrid_to = os.getenv("SENDGRID_TO_EMAIL")
        if all([sendgrid_api_key, sendgrid_to]):
            notification_config["sendgrid"] = {
                "api_key": sendgrid_api_key,
                "to_email": sendgrid_to,
            }

        # Mailgun
        mailgun_domain = os.getenv("MAILGUN_DOMAIN")
        mailgun_api_key = os.getenv("MAILGUN_API_KEY")
        mailgun_to = os.getenv("MAILGUN_TO_EMAIL")
        if all([mailgun_domain, mailgun_api_key, mailgun_to]):
            notification_config["mailgun"] = {
                "domain": mailgun_domain,
                "api_key": mailgun_api_key,
                "to_email": mailgun_to,
            }

        if notification_config:
            default_config["notifications"] = notification_config

        return default_config

    def extract_target_text(self, html_content: str) -> str | None:
        """Extract the specific paragraph about swimming school registration"""
        soup = BeautifulSoup(html_content, "html.parser")

        keywords = self.config["target_text_keywords"]

        # Search in all text elements (using 'string' instead of deprecated 'text')
        for element in soup.find_all(string=True):
            if element and isinstance(element, str):
                text = element.strip()
                if (
                    text
                    and len(text) > self.config["min_text_length"]
                    and all(keyword.lower() in text.lower() for keyword in keywords)
                ):
                    clean_text = re.sub(r"\s+", " ", text).strip()
                    return clean_text

        # Alternative search in specific elements
        for tag in ["p", "div", "span", "article"]:
            elements = soup.find_all(tag)
            for elem in elements:
                if elem:
                    text = elem.get_text(strip=True)
                    if (
                        text
                        and isinstance(text, str)
                        and len(text) > self.config["min_text_length"]
                        and all(keyword.lower() in text.lower() for keyword in keywords)
                    ):
                        clean_text = re.sub(r"\s+", " ", text).strip()
                        return clean_text

        logger.warning("Target text not found on the page")
        return None

    def fetch_page_content(self) -> str | None:
        """Fetch the webpage content"""
        try:
            response = self.session.get(self.config["url"], timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching webpage: {e}")
            return None

    def get_cached_content(self) -> dict[str, Any] | None:
        """Get previously cached content"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading cache: {e}")
        return None

    def save_cached_content(self, text: str, text_hash: str):
        """Save content to cache"""
        cache_data = {
            "text": text,
            "hash": text_hash,
            "timestamp": datetime.now().isoformat(),
            "url": self.config["url"],
        }
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _dummy_check_for_changes(self):
        """Dummy monitoring function"""
        logger.info("Checking for changes...")

        html_content = self.fetch_page_content()
        if not html_content:
            return

        current_text = self.extract_target_text(html_content)
        if not current_text:
            logger.warning("Could not extract target text from page")
            return

        print(current_text)

        return None

    def check_for_changes(self):
        """Main monitoring function"""
        logger.info("Checking for changes...")

        html_content = self.fetch_page_content()
        if not html_content:
            return

        current_text = self.extract_target_text(html_content)
        if not current_text:
            logger.warning("Could not extract target text from page")
            return

        current_hash = hashlib.md5(current_text.encode("utf-8")).hexdigest()
        cached_data = self.get_cached_content()

        if cached_data is None:
            logger.info("First run - saving current content to cache")
            self.save_cached_content(current_text, current_hash)
            return

        cached_hash = cached_data.get("hash")
        cached_text = cached_data.get("text", "")

        if current_hash != cached_hash:
            logger.info("CHANGE DETECTED!")

            subject = "🚨 Website Update Detected - PUC Swimming Registration"
            message = f"""Content change detected on the PUC swimming website!

URL: {self.config["url"]}
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

PREVIOUS CONTENT:
{cached_text}

NEW CONTENT:
{current_text}

This is an automated alert from your website monitor.
"""

            # Send notifications via all configured methods
            self.notification_manager.send_all_notifications(subject, message)

            # Update cache
            self.save_cached_content(current_text, current_hash)

            logger.info("Alerts sent and cache updated")
        else:
            logger.info("No changes detected")

    def run_forever(self):
        """Run the monitor continuously"""
        logger.info(f"Starting website monitor for URL: {self.config['url']}")
        logger.info(f"Check interval: {self.config['check_interval_minutes']} minutes")

        while True:
            try:
                self.check_for_changes()
                sleep_seconds = self.config["check_interval_minutes"] * 60
                logger.info(
                    f"Sleeping for {self.config['check_interval_minutes']} minutes..."
                )
                time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(300)


def main():
    # Use default config file in configs folder
    config_path = "configs/basic.json"

    # Check if config exists, otherwise try to find it
    config_file = Path(config_path)
    if not config_file.exists():
        # Try looking in the package directory
        package_config = Path(__file__).parent.parent.parent / config_path
        if package_config.exists():
            config_path = str(package_config)

    monitor = WebsiteMonitor(config_path)
    # monitor.run_forever()
    monitor._dummy_check_for_changes()


if __name__ == "__main__":
    main()
