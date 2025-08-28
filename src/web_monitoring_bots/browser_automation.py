import hashlib
import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from web_monitoring_bots.monitor import NotificationManager


class PlaywrightWebMonitor:
    """Monitor authenticated websites using Playwright"""

    def __init__(self, headless=True):
        self.playwright = sync_playwright().start()
        self.base_dir = Path().absolute()
        self.cache_file = self.base_dir / "content_cache_2.json"
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        # Create context with persistent session
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        self.page = self.context.new_page()

    def login(
        self,
        login_url,
        username,
        password,
        username_selector="input[name='username']",
        password_selector="input[name='password']",
        login_button="button[type='submit']",
    ):
        """Login using Playwright - handles static login pages"""
        try:
            self.page.goto(login_url)

            # Fill login form
            self.page.fill(username_selector, username)
            self.page.fill(password_selector, password)

            # Click login button and wait for navigation
            with self.page.expect_navigation():
                self.page.click(login_button)

            print(f"✅ Logged in successfully. Current URL: {self.page.url}")
            return True

        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False

    def login_with_popup(  # noqa: C901
        self,
        base_url,
        username,
        password,
        connect_button_selector="button:has-text('SE CONNECTER')",
        username_selector="input[placeholder*='Adresse Email'], input[type='email'], #email",  # noqa: E501
        password_selector="input[placeholder*='Mot de passe'], input[type='password'], #password",  # noqa: E501
        submit_button_selector="button:has-text('SUIVANT'), button[type='submit']",
        wait_after_login=3000,
    ):
        """
        Login using a popup/modal that appears after clicking a connect button.
        This is specifically designed for MonClub-style login flows.

        Args:
            base_url: The main page URL
            username: Username/email for login
            password: Password for login
            connect_button_selector: Selector for the initial "SE CONNECTER" button
            username_selector: Selector for the email/username field in the popup
            password_selector: Selector for the password field in the popup
            submit_button_selector: Selector for the submit button in the popup
            wait_after_login: Time to wait after login (ms)

        Returns:
            Boolean indicating success
        """
        try:
            print(f"🌐 Navigating to {base_url}")
            self.page.goto(base_url)
            self.page.wait_for_load_state("networkidle")

            # Look for and click the SE CONNECTER button
            print("🔍 Looking for SE CONNECTER button...")

            # Try multiple possible selectors for the connect button
            connect_selectors = [
                connect_button_selector,
                "button:has-text('SE CONNECTER')",
                "a:has-text('SE CONNECTER')",
                "[class*='login']",
                "[class*='connect']",
                ".btn-login",
                "#login-button",
            ]

            button_clicked = False
            for selector in connect_selectors:
                try:
                    if self.page.is_visible(selector, timeout=2000):
                        print(f"  ✓ Found button with selector: {selector}")
                        self.page.click(selector)
                        button_clicked = True
                        break
                except Exception as e:
                    print(f"  ⚠️ Error finding button: {e}")
                    continue

            if not button_clicked:
                print("❌ Could not find SE CONNECTER button")
                return False

            # Wait for the login modal/popup to appear
            print("⏳ Waiting for login popup to appear...")
            self.page.wait_for_timeout(1000)  # Brief wait for animation

            # Try to find and fill the email field
            print("📧 Entering email address...")
            email_selectors = [
                username_selector,
                "input[placeholder*='email' i]",
                "input[placeholder*='adresse' i]",
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "#email",
                ".email-input",
            ]

            email_filled = False
            for selector in email_selectors:
                try:
                    if self.page.is_visible(selector, timeout=2000):
                        print(f"  ✓ Found email field with selector: {selector}")
                        self.page.fill(selector, username)
                        email_filled = True
                        break
                except Exception as e:
                    print(f"  ⚠️ Error finding email field: {e}")
                    continue

            if not email_filled:
                print("❌ Could not find email field")
                return False

            # Try to find and fill the password field
            print("🔐 Entering password...")
            password_selectors = [
                password_selector,
                "input[placeholder*='mot de passe' i]",
                "input[placeholder*='password' i]",
                "input[type='password']",
                "input[name='password']",
                "#password",
                ".password-input",
            ]

            password_filled = False
            for selector in password_selectors:
                try:
                    if self.page.is_visible(selector, timeout=2000):
                        print(f"  ✓ Found password field with selector: {selector}")
                        self.page.fill(selector, password)
                        password_filled = True
                        break
                except Exception as e:
                    print(f"  ⚠️ Error finding password field: {e}")
                    continue

            if not password_filled:
                print("❌ Could not find password field")
                return False

            # Find and click the submit button
            print("🚀 Submitting login form...")
            submit_selectors = [
                submit_button_selector,
                "button:has-text('SUIVANT')",
                "button:has-text('Connexion')",
                "button:has-text('Login')",
                "button:has-text('Se connecter')",
                "button[type='submit']",
                ".submit-button",
                ".btn-submit",
            ]

            submit_clicked = False
            for selector in submit_selectors:
                try:
                    if self.page.is_visible(selector, timeout=2000):
                        print(f"  ✓ Found submit button with selector: {selector}")
                        # Some sites need a small delay before clicking submit
                        self.page.wait_for_timeout(500)
                        self.page.click(selector)
                        submit_clicked = True
                        break
                except Exception as e:
                    print(f"❌ Error finding submit button: {e}, but continuing...")
                    continue

            if not submit_clicked:
                print("❌ Could not find submit button")
                return False

            # Wait for login to complete
            print("⏳ Waiting for login to complete...")
            self.page.wait_for_timeout(wait_after_login)

            # Debug: Print current URL and page title
            print(f"🔍 Current URL after login attempt: {self.page.url}")
            try:
                page_title = self.page.title()
                print(f"🔍 Page title: {page_title}")
            except Exception as e:
                print(f"🔍 Error getting page title: {e}")
                print("🔍 Could not get page title")

            # Check if login was successful by looking for indicators
            # The SE CONNECTER button should be gone or replaced
            login_success = False

            # Check if we're still on the same page but logged in
            try:
                # Look for signs of being logged in
                logged_in_indicators = [
                    "button:has-text('MON COMPTE')",
                    "button:has-text('DÉCONNEXION')",
                    "button:has-text('Mon Profil')",
                    "[class*='user-menu']",
                    "[class*='logged-in']",
                    ".user-profile",
                    ".logout-button",
                    # Add more common French indicators
                    "button:has-text('PROFIL')",
                    "button:has-text('COMPTE')",
                    "a:has-text('Déconnexion')",
                    "a:has-text('Mon compte')",
                ]

                print("🔍 Checking for logged-in indicators...")
                for indicator in logged_in_indicators:
                    try:
                        if self.page.is_visible(indicator, timeout=1000):
                            login_success = True
                            print(f"  ✓ Found logged-in indicator: {indicator}")
                            break
                        else:
                            print(f"  ⚪ Not found: {indicator}")
                    except Exception as e:
                        print(f"  ⚠️ Error checking {indicator}: {e}")

                # Also check if the SE CONNECTER button is gone
                if not login_success:
                    try:
                        print("🔍 Checking if SE CONNECTER button is still visible...")
                        se_connecter_visible = self.page.is_visible(
                            "button:has-text('SE CONNECTER')", timeout=5000
                        )
                        if not se_connecter_visible:
                            login_success = True
                            print("  ✓ SE CONNECTER button is gone (good sign)")
                        else:
                            print(
                                "  ❌ SE CONNECTER button is still visible"
                                " (login may have failed)"
                            )
                    except Exception as e:
                        print(f"  ⚠️ Error checking SE CONNECTER button: {e}")
                        # If we can't find the button, assume it's gone (login success)
                        login_success = True
                        print(
                            "  ✓ Cannot find SE CONNECTER button"
                            " (assuming login success)"
                        )

            except Exception as e:
                print(f"  ⚠️ Error checking login status: {e}")
                pass

            if login_success:
                print(f"✅ Login successful! Current URL: {self.page.url}")
                # Take a screenshot to verify
                self.take_screenshot("after_login.png")
                return True
            else:
                print("⚠️ Login may have failed - could not confirm login status")
                self.take_screenshot("login_attempt.png")
                return False

        except Exception as e:
            print(f"❌ Login failed with error: {e}")
            self.take_screenshot("login_error.png")
            return False

    def navigate_to_page(self, url):
        """Navigate to specific page"""
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def scroll_to_load_all_content(self, max_scrolls: int = 50, wait_time: int = 2000):
        """
        Scroll through the page to load all dynamic content.

        Args:
            max_scrolls: Maximum number of scroll attempts
            wait_time: Time to wait between scrolls in milliseconds

        Returns:
            Number of scrolls performed
        """
        print("🔄 Starting to scroll through the page...")

        # Get initial height
        last_height = self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0

        for i in range(max_scrolls):
            # Scroll to bottom
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Wait for new content to load
            self.page.wait_for_timeout(wait_time)

            # Calculate new scroll height
            new_height = self.page.evaluate("document.body.scrollHeight")

            scroll_count += 1

            # If height hasn't changed, we've reached the bottom
            if new_height == last_height:
                print(f"✅ Reached end of page after {scroll_count} scrolls")
                break

            last_height = new_height

            # Print progress every 5 scrolls
            if (i + 1) % 5 == 0:
                print(f"  📜 Scrolled {i + 1} times, current height: {new_height}px")

        # Scroll back to top for good measure
        self.page.evaluate("window.scrollTo(0, 0)")
        self.page.wait_for_timeout(500)

        return scroll_count

    def extract_course_headings(self) -> list[dict[str, str]]:  # noqa: C901
        """
        Extract course headings from the blocks on the page.
        Based on the DOM structure visible in the screenshot, this targets
        course cards within MuiPaper containers.

        Returns:
            List of dictionaries containing course information
        """
        print("🔍 Extracting course headings from MUI card structure...")

        # Optimized selectors to reduce duplicates - ordered by specificity
        # Start with most specific and stop when we find good results
        selectors_to_try = [
            # Most specific - target paragraph elements within MUI cards
            # (this seems to work best)
            "div[class*='MuiPaper-root'] p:has-text('|')",
            # Backup selectors in case the above doesn't work
            "div[class*='MuiPaper-root'] p",
            "div[class*='MuiPaper-root'] div[class*='MuiTypography']:has-text('|')",
            "div[class*='MuiPaper-root'] *:has-text('|')",
            # Broader fallback selectors
            "div:has-text('NATATION')",
            "div:has-text('TRIATHLON')",
            "*:has-text(' | ')",  # Any element with pipe separator
        ]

        courses = []
        found_elements = []
        good_results_found = False

        # Try each selector - stop early if we find good results
        for selector in selectors_to_try:
            if good_results_found and len(found_elements) > 5:
                print(
                    "  ✓ Stopping early - found sufficient results with"
                    " previous selectors"
                )
                break
            try:
                elements = self.page.query_selector_all(selector)
                if elements:
                    print(
                        f"  ✓ Found {len(elements)} elements with selector: {selector}"
                    )

                    for elem in elements:
                        try:
                            text = (
                                elem.text_content().strip()  # pyright: ignore[reportOptionalMemberAccess]
                                if elem.text_content()
                                else ""
                            )

                            # Filter for course-like content
                            # Look for text that contains pipe separators
                            # and course keywords
                            if (
                                text
                                and len(text) > 15
                                and len(text) < 300  # Reasonable length
                                and "|" in text
                                and any(
                                    keyword in text.upper()
                                    for keyword in [
                                        "NATATION",
                                        "TRIATHLON",
                                        "LICENCE",
                                        "ECOLE",
                                        "AQUA",
                                        "FITNESS",
                                        "COURS",
                                        "ENTRAINEMENT",
                                    ]
                                )
                            ):
                                # Avoid duplicates and overly generic text
                                if (
                                    text
                                    not in [course["heading"] for course in courses]
                                    and not text.startswith(
                                        "€"
                                    )  # Skip price-only elements
                                    and "disponibles" not in text.lower()
                                ):  # Skip availability text
                                    found_elements.append((selector, elem, text))

                        except Exception as e:
                            print(f"    ⚠️ Error processing element text: {e}")
                            continue

                    # Mark that we found good results with this selector
                    if len([e for e in found_elements if e[0] == selector]) > 0:
                        good_results_found = True

            except Exception as e:
                print(f"  ⚠️ Error with selector {selector}: {e}")
                continue

        # Process found elements and extract detailed information
        for selector, elem, heading_text in found_elements:
            try:
                course_info = {
                    "heading": heading_text,
                    "selector_used": selector,
                    "raw_text": heading_text,
                }

                # Parse the heading to extract structured information
                # Expected format: "ACTIVITY | CODE | Description | Day Time"
                parts = [part.strip() for part in heading_text.split("|")]
                if len(parts) >= 2:
                    course_info["activity"] = parts[0]
                    if len(parts) >= 2:
                        course_info["code"] = parts[1]
                    if len(parts) >= 3:
                        course_info["description"] = parts[2]
                    if len(parts) >= 4:
                        course_info["schedule"] = parts[3]

                # Try to find the parent card container for additional info
                try:
                    parent_card = elem.evaluate_handle(
                        "el => el.closest('div[class*='MuiPaper-root'],"
                        "div[class*='card'], div[class*='MuiBox-root']')"
                    )

                    # Try to extract price information from the card
                    try:
                        price_selectors = [
                            "*:has-text('€')",
                            "*:has-text('partir de')",
                            "*[class*='price']",
                            "div:has-text('€'):not(:has-text('|'))",
                            # Price divs without course info
                        ]

                        for price_selector in price_selectors:
                            price_elem = parent_card.query_selector(price_selector)
                            if price_elem:
                                price_text = price_elem.text_content().strip()
                                if (
                                    price_text
                                    and "€" in price_text
                                    and len(price_text) < 50
                                ):
                                    course_info["price"] = price_text
                                    break
                    except Exception as e:
                        print(f"  ⚠️ Error extracting price info: {e}")
                        pass

                    # Try to extract location information
                    try:
                        location_selectors = [
                            "*:has-text('Cité Universitaire')",
                            "*:has-text('Paris')",
                            "*:has-text('75014')",
                            "div:has-text('Lieu')",
                        ]

                        for loc_selector in location_selectors:
                            location_elem = parent_card.query_selector(loc_selector)
                            if location_elem:
                                location_text = location_elem.text_content().strip()
                                if location_text and len(location_text) < 100:
                                    course_info["location"] = location_text
                                    break
                    except Exception as e:
                        print(f"  ⚠️ Error extracting location info: {e}")
                        pass

                    # Try to extract date information
                    try:
                        date_selectors = [
                            "*:has-text('Date de début')",
                            "*:has-text('Date de fin')",
                            "div:has-text('/')",  # Date format DD/MM/YYYY
                        ]

                        for date_selector in date_selectors:
                            date_elem = parent_card.query_selector(date_selector)
                            if date_elem:
                                date_text = date_elem.text_content().strip()
                                if date_text and (
                                    "/" in date_text or "202" in date_text
                                ):
                                    course_info["dates"] = date_text
                                    break
                    except Exception as e:
                        print(f"  ⚠️ Error extracting date info: {e}")
                        pass

                except Exception as e:
                    print(f"  ⚠️ Error extracting additional info: {e}")

                courses.append(course_info)

            except Exception as e:
                print(f"  ⚠️ Error processing element: {e}")
                continue

        # Clean and deduplicate courses
        unique_courses = []
        seen_courses = set()

        for course in courses:
            # Clean the heading text - remove price info that got concatenated
            heading = course["heading"]

            # Remove price text that got mixed in
            if "À partir de" in heading:
                heading = heading.split("À partir de")[0].strip()
            if "€" in heading and not heading.startswith("€"):
                # Remove everything after the first € symbol if it's not a
                # price-only element
                parts = heading.split("€")
                if len(parts) > 1 and "|" in parts[0]:
                    heading = parts[0].strip()

            # Remove trailing "S'inscrire" text
            if heading.endswith("S'inscrire"):
                heading = heading[:-10].strip()

            # Update the cleaned heading
            course["heading"] = heading
            course["raw_text"] = heading

            # Re-parse the cleaned heading
            parts = [part.strip() for part in heading.split("|")]
            if len(parts) >= 2:
                course["activity"] = parts[0]
                if len(parts) >= 2:
                    course["code"] = parts[1]
                if len(parts) >= 3:
                    course["description"] = parts[2]
                if len(parts) >= 4:
                    course["schedule"] = parts[3]

            # Create a unique identifier based on activity, code, and description
            # This handles cases where the same course appears multiple times
            unique_id = (
                f"{course.get('activity', '')}-{course.get('code', '')}-"
                f"{course.get('description', '')}"
            )

            # Only add if we haven't seen this course before
            if unique_id not in seen_courses and len(heading.strip()) > 10:
                unique_courses.append(course)
                seen_courses.add(unique_id)

        print(f"✅ Found {len(unique_courses)} unique course headings")

        # Print detailed results for debugging
        for i, course in enumerate(unique_courses[:5], 1):  # Show first 5 for debugging
            print(f"  {i}. Activity: {course.get('activity', 'N/A')}")
            print(f"     Code: {course.get('code', 'N/A')}")
            print(f"     Description: {course.get('description', 'N/A')}")
            print(f"     Schedule: {course.get('schedule', 'N/A')}")
            if course.get("price"):
                print(f"     Price: {course['price']}")
            print(f"     Selector: {course['selector_used']}")
            print()

        return unique_courses

    def extract_all_offerings(
        self, scroll_first: bool = True
    ) -> tuple[list[dict[str, str]], str]:
        """
        Main method to scroll through the page and extract all course offerings.

        Args:
            scroll_first: Whether to scroll through the page first to load all content

        Returns:
            List of course information dictionaries
        """
        if scroll_first:
            # First, scroll to load all content
            self.scroll_to_load_all_content()

        # Then extract the course headings
        courses = self.extract_course_headings()

        # Print summary
        print("\n📊 Summary of extracted courses:")
        combined_string = ""

        # for i, course in enumerate(courses, 1):
        #     print(
        #         f"  {i}. {course['heading'][:80]}"
        #         f"{'...' if len(course['heading']) > 80 else ''}"
        #     )
        #     if "price" in course:
        #         print(f"     💰 {course['price']}")
        #     if "day" in course:
        #         print(f"     📅 {course['day']}")

        for i, course in enumerate(courses, 1):
            combined_string += f"  {i}. {course['heading'][:100]}"
            combined_string += f"{'...' if len(course['heading']) > 100 else ''}"
            if "price" in course:
                combined_string += f"     💰 {course['price']}"
            if "day" in course:
                combined_string += f"     📅 {course['day']}"
            combined_string += "\n"
        print(combined_string)
        return courses, combined_string

    def extract_text_by_selector(self, selector):
        """Extract text using CSS selector"""
        try:
            element = self.page.wait_for_selector(selector, timeout=10000)
            return (
                element.text_content().strip()  # pyright: ignore[reportOptionalMemberAccess]
                if element.text_content()  # pyright: ignore[reportOptionalMemberAccess]
                else ""
            )
        except Exception as e:
            print(f"❌ Could not find element: {e}")
            return None

    def extract_multiple_texts(self, selector):
        """Extract text from multiple elements"""
        try:
            elements = self.page.query_selector_all(selector)
            return [
                elem.text_content().strip()  # pyright: ignore[reportOptionalMemberAccess]
                for elem in elements
                if elem.text_content().strip()  # pyright: ignore[reportOptionalMemberAccess]
            ]
        except Exception as e:
            print(f"❌ Could not find elements: {e}")
            return []

    def click_element(self, selector):
        """Click an element"""
        try:
            self.page.click(selector)
            self.page.wait_for_timeout(1000)
            return True
        except Exception as e:
            print(f"❌ Could not click element: {e}")
            return False

    def save_state(self, filename="auth_state.json"):
        """Save authentication state"""
        self.context.storage_state(path=filename)
        print(f"✅ Authentication state saved to {filename}")

    def load_state(self, filename="auth_state.json"):
        """Load authentication state"""
        if os.path.exists(filename):
            # Create new context with saved state
            self.context.close()
            self.context = self.browser.new_context(storage_state=filename)
            self.page = self.context.new_page()
            print(f"✅ Authentication state loaded from {filename}")
            return True
        return False

    def get_cached_content(self) -> dict[str, Any] | None:
        """Get previously cached content"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache: {e}")
        return None

    def save_cached_content(self, text: str, text_hash: str):
        """Save content to cache"""
        cache_data = {
            "text": text,
            "hash": text_hash,
            "timestamp": datetime.now(ZoneInfo("Europe/Paris")).isoformat(),
        }
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def take_screenshot(self, filename="screenshot.png"):
        """Take screenshot"""
        self.page.screenshot(path=filename)
        print(f"📸 Screenshot saved as {filename}")

    def get_page_source(self):
        """Get HTML source"""
        return self.page.content()

    def cleanup(self):
        """Cleanup resources"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def find_config_from_env() -> dict[str, Any]:
    default_config = {
        "url": "",
        "notifications": {},
        "username": "",
        "password": "",
    }

    # Override with environment variables
    env_url = os.getenv("MONCLUB_URL")
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

    default_config["notifications"] = notification_config

    # Username and password
    username = os.getenv("MONCLUB_USERNAME")
    password = os.getenv("MONCLUB_PASSWORD")
    if username and password:
        default_config["username"] = username.strip("'\"")
        default_config["password"] = password.strip("'\"")

    return default_config


def main():
    config = find_config_from_env()

    # Initialize the monitor
    monitor = PlaywrightWebMonitor(headless=True)  # Set to True for headless mode
    notification_manager = NotificationManager(config.get("notifications", {}))

    # Initialize variables outside try block to avoid scope issues
    combined_string = ""
    courses = []

    try:
        # For MonClub app with popup login
        login_success = monitor.login_with_popup(
            base_url=config["url"],
            # base_url="https://puc.monclub.app/app/60c3279efd32790020c20a2e",
            username=config["username"],
            password=config["password"],
        )

        if login_success:
            # After successful login, navigate to activities if needed
            # The login might already land you on the activities page
            # monitor.navigate_to_page("https://your-monclub-url.com/activities")

            # Wait a bit for the page to fully load
            monitor.page.wait_for_timeout(2000)

            # Extract all course offerings
            courses, combined_string = monitor.extract_all_offerings(scroll_first=True)

            with open("course_offerings.json", "w", encoding="utf-8") as f:
                json.dump(courses, f, ensure_ascii=False, indent=2)

            print(f"\n💾 Saved {len(courses)} courses to course_offerings.json")

            # Take a screenshot for reference
            monitor.take_screenshot("final_page.png")

            # Save authentication state for future use
            monitor.save_state()

        else:
            print("❌ Login failed, cannot proceed with course extraction")
            combined_string = "Login failed - unable to extract course offerings"

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        notification_manager.send_telegram(
            message="PUC Natation Monitor\n"
            + str(e)
            + "\n"
            + traceback.format_exc()
            + "\n"
            + "Please check the logs for more details."
        )
    else:
        current_hash = hashlib.md5(combined_string.encode("utf-8")).hexdigest()
        # Check if there are any changes in the course offerings
        cached_content = monitor.get_cached_content()

        if not cached_content:
            print("🔍 No cached content found, saving current content")
            monitor.save_cached_content(combined_string, current_hash)
            print(f"🔍 Current hash saved to cache: {current_hash}")
        else:
            if cached_content["hash"] != current_hash:
                print("🔍 Changes detected in course offerings")
                notification_manager.send_telegram(
                    message="New PUC Natation courses found:\n" + combined_string,
                )
                notification_manager.send_discord(
                    message="New PUC Natation courses found:\n" + combined_string,
                )
                monitor.save_cached_content(combined_string, current_hash)
            else:
                print("🔍 No changes detected in course offerings")
                notification_manager.send_telegram(
                    message="No changes detected in course offerings"
                    + f"\n{cached_content['timestamp']}",
                )
                notification_manager.send_discord(
                    message="No changes detected in course offerings"
                    + f"\n{cached_content['timestamp']}",
                )
                monitor.save_cached_content(combined_string, current_hash)
    finally:
        # Clean up resources
        monitor.cleanup()


# Example usage
if __name__ == "__main__":
    main()
