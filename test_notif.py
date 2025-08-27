import json

from web_monitoring_bots.monitor import NotificationManager

# Load your config
with open("configs/basic.json") as f:
    config = json.load(f)

# Test notifications
nm = NotificationManager(config.get("notifications", {}))
nm.send_discord("Test Alert: This is a test notification from your website monitor!")
nm.send_telegram("Test Alert: This is a test notification from your website monitor!")
