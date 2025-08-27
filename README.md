# Web Monitoring Bots

A collection of bots for monitoring static content on webpages, and sending out alerts and notifications based on it.

## 🚀 Quick Setup Guides for Notification Methods

### 🟣 Discord (Recommended - 100% Free & Easy)

**Why Discord?** Instant notifications, completely free, works on all devices, no phone number required.

#### Setup Steps (5 minutes):

1. **Create Discord server** (or use existing):

   - Open Discord → Click "+" → "Create My Own" → "For me and my friends"

2. **Create notification channel**:

   - Right-click your server → "Create Channel" → Name it "website-alerts"

3. **Create webhook**:

   - Right-click the channel → "Edit Channel" → "Integrations" → "Webhooks"
   - "New Webhook" → Copy the webhook URL

4. **Add to configuration**:

   ```bash
   # For GitHub Actions, add this secret:
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/your-webhook-url

   # For config.json:
   "discord": {
     "webhook_url": "https://discord.com/api/webhooks/123456789/your-webhook-url"
   }
   ```

---

### 📱 Telegram (Also Free & Excellent)

**Why Telegram?** Free worldwide, instant push notifications, very reliable.

#### Setup Steps (3 minutes):

1. **Create a Telegram bot**:

   - Open Telegram app
   - Search for `@BotFather`
   - Send `/start` then `/newbot`
   - Choose a name: "PUC Website Monitor"
   - Choose a username: "puc_monitor_bot" (must end with "bot")
   - Save the bot token you receive

2. **Get your chat ID**:

   - Start a conversation with your new bot
   - Send any message to the bot
   - Go to: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789}` - that number is your chat ID

3. **Add to configuration**:

   ```bash
   # For GitHub Actions:
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here

   # For config.json:
   "telegram": {
     "bot_token": "your_bot_token_here",
     "chat_id": "your_chat_id_here"
   }
   ```

---

### 📧 Mailgun (Free Email - 5,000 emails/month)

**Why Mailgun?** No personal email required, very reliable, generous free tier.

#### Setup Steps (5 minutes):

1. **Sign up** at [mailgun.com](https://mailgun.com)
2. **Verify your email** and complete registration
3. **Go to Dashboard** → "Sending" → "Domains"
4. **Use sandbox domain** (already created) or add your own domain
5. **Get API key** from "Settings" → "API Keys"
6. **Add authorized recipients** (your email where you want notifications)

7. **Add to configuration**:

   ```bash
   # For GitHub Actions:
   MAILGUN_DOMAIN=sandbox123abc.mailgun.org
   MAILGUN_API_KEY=your-api-key-here
   MAILGUN_TO_EMAIL=your-real-email@example.com

   # For config.json:
   "mailgun": {
     "domain": "sandbox123abc.mailgun.org",
     "api_key": "your-api-key-here",
     "to_email": "your-real-email@example.com"
   }
   ```

---

## 🏆 Recommended Setup Combinations

### **For Instant Notifications**: Discord + Telegram

- Both are free and instant
- Discord for desktop/web, Telegram for mobile
- High reliability with dual channels

---

## 🔧 Complete GitHub Actions Setup

1. **Add your repository secrets** (Settings → Secrets and variables → Actions):

   ```
   URL=https://www.puc.fr/natation
   DISCORD_WEBHOOK_URL=your_discord_webhook
   TELEGRAM_BOT_TOKEN=your_telegram_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

2. **Create the workflow file** `.github/workflows/website-monitor.yml` with the provided YAML

3. **Test it**: Go to Actions tab → Website Monitor → Run workflow

---

## 🛠️ Local Testing

Test your notifications before deployment:

```python
# test_notifications.py
from monitor import NotificationManager
import json

# Load your config
with open('config.json', 'r') as f:
    config = json.load(f)

# Test notifications
nm = NotificationManager(config.get('notifications', {}))
nm.send_all_notifications(
    "Test Alert",
    "This is a test notification from your website monitor!"
)
```

Run: `python test_notifications.py`

---

## 📊 Monitoring Your Monitor

### Check if it's working:

- **Discord/Telegram**: You'll see messages in your channels
- **GitHub Actions**: Check the "Actions" tab for green checkmarks
- **Server**: Use `sudo journalctl -u website-monitor -f`
- **Docker**: Use `docker logs -f puc-website-monitor`

### Common troubleshooting:

- **No notifications**: Check your webhook URLs and tokens
- **"Target text not found"**: The website structure might have changed
- **Rate limiting**: The current 4-minute interval should be fine
- **Email issues**: Make sure you're using App Passwords, not regular passwords

---
