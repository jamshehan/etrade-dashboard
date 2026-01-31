from playwright.sync_api import sync_playwright, Page, Browser
from pathlib import Path
from datetime import datetime, timedelta
import time
import config


class ETradeScraper:
    """
    Web scraper for eTrade checking account transactions

    Uses a persistent browser profile so that eTrade's "trust this device"
    cookie survives between runs. After initial MFA setup, subsequent runs
    can execute headlessly without user intervention.
    """

    # Persistent browser profile directory (preserves cookies/device trust)
    BROWSER_PROFILE_DIR = config.BASE_DIR / 'data' / 'browser_profile'

    def __init__(self, username: str = None, password: str = None, headless: bool = None):
        self.username = username or config.ETRADE_USERNAME
        self.password = password or config.ETRADE_PASSWORD
        self.download_dir = config.DOWNLOAD_DIR
        self.headless = headless if headless is not None else config.HEADLESS
        self.timeout = config.SCRAPER_TIMEOUT

        # Ensure browser profile directory exists
        self.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        if not self.username or not self.password:
            raise ValueError("eTrade credentials not configured. Set ETRADE_USERNAME and ETRADE_PASSWORD in .env file")

    def download_transactions(self, start_date: str = None, end_date: str = None) -> Path:
        """
        Download transaction CSV from eTrade

        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            Path to downloaded CSV file
        """
        with sync_playwright() as playwright:
            # Use persistent context to preserve cookies & device trust
            # Use channel="chrome" to use a stock Chrome-like fingerprint
            # and avoid eTrade detecting Playwright automation
            print(f"Launching browser (headless={self.headless}, profile={self.BROWSER_PROFILE_DIR})")
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.BROWSER_PROFILE_DIR),
                headless=self.headless,
                channel="chrome",
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            page = context.new_page()

            try:
                print("Navigating to eTrade login page...")
                page.goto("https://us.etrade.com/e/t/user/login", timeout=self.timeout)

                # Wait for page to load
                time.sleep(2)

                # Perform login
                self._login(page)

                # Handle MFA if needed
                self._handle_mfa(page)

                # Use the most recent page in case eTrade opened a new tab
                pages = context.pages
                if len(pages) > 1:
                    print(f"Multiple pages detected ({len(pages)}), using most recent")
                    page = pages[-1]

                # Navigate directly to download page
                csv_path = self._download_csv(page, start_date, end_date)

                print(f"Successfully downloaded transactions to: {csv_path}")
                return csv_path

            except Exception as e:
                # Take screenshot on error for debugging
                screenshot_path = self.download_dir / f"error_screenshot_{int(time.time())}.png"
                page.screenshot(path=str(screenshot_path))
                print(f"Error screenshot saved to: {screenshot_path}")
                raise Exception(f"Scraper error: {str(e)}")

            finally:
                context.close()

    def _login(self, page: Page):
        """
        Perform login to eTrade
        """
        print("Logging in...")

        try:
            # Wait for username field
            page.wait_for_selector('#USER', timeout=self.timeout)

            # Fill username
            page.fill('#USER', self.username)

            # Fill password
            page.fill('#password', self.password)

            # Click login button and wait for navigation
            print("Submitting credentials...")
            page.click('#mfaLogonButton')

            # Wait for page to navigate away from login page
            page.wait_for_url(lambda url: '/user/login' not in url, timeout=self.timeout)

            print("Login credentials submitted, navigated to next page")
            time.sleep(2)

        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    def _handle_mfa(self, page: Page):
        """
        Handle MFA if required
        """
        print("Checking for MFA...")

        try:
            # Wait for page to fully load and all redirects to complete
            print("Waiting for page to finish loading and redirects to complete...")
            page.wait_for_load_state('networkidle', timeout=self.timeout)
            time.sleep(2)

            current_url = page.url
            print(f"Current URL after load: {current_url}")

            # Check if we bounced back to the actual login page (session expired)
            # Note: /etx/pxy/login is a post-login proxy page, NOT the login form
            if "/e/t/user/login" in current_url or "/user/login" in current_url and "/etx/" not in current_url:
                print("WARNING: Redirected back to login page!")
                print("This may mean eTrade rejected the session.")
                print("Attempting to re-login...")
                self._login(page)
                page.wait_for_load_state('networkidle', timeout=self.timeout)
                time.sleep(2)
                current_url = page.url
                print(f"URL after re-login: {current_url}")

            # Check if we're on the send OTP page or verify page
            if "sendotpcode" in current_url:
                print("\n" + "="*60)
                print("MFA REQUIRED — MANUAL ACTION NEEDED")
                print("="*60)
                print("1. In the browser window, click 'Send Security Code'")
                print("2. Check your phone for the SMS code from eTrade")
                print("3. Enter the code in the browser")
                print("4. CHECK 'Save this device' to skip MFA next time!")
                print("5. Click Submit")
                print("="*60 + "\n")

                # Wait for user to complete the full MFA flow
                print("Waiting for MFA completion (up to 3 minutes)...")
                try:
                    page.wait_for_url(
                        lambda url: "sendotpcode" not in url and "verifyotpcode" not in url,
                        timeout=180000
                    )
                except Exception as e:
                    print(f"Error waiting for MFA: {e}")
                    print(f"Current URL: {page.url}")
                    raise Exception("Timeout or error waiting for MFA completion")

                print("MFA completed successfully")
                time.sleep(3)

            elif "verifyotpcode" in current_url:
                print("\n" + "="*60)
                print("MFA CODE ENTRY — MANUAL ACTION NEEDED")
                print("="*60)
                print("1. Enter the SMS code in the browser")
                print("2. CHECK 'Save this device' to skip MFA next time!")
                print("3. Click Submit")
                print("="*60 + "\n")

                print("Waiting for MFA completion (up to 3 minutes)...")
                try:
                    page.wait_for_url(
                        lambda url: "verifyotpcode" not in url,
                        timeout=180000
                    )
                except Exception as e:
                    print(f"Error waiting for MFA: {e}")
                    print(f"Current URL: {page.url}")
                    raise Exception("Timeout or error waiting for MFA completion")

                print("MFA completed successfully")
                time.sleep(3)

            else:
                print(f"No MFA required - device already trusted (URL: {current_url})")

            # Wait for post-login redirects to fully settle
            print("Waiting for post-login navigation to settle...")
            time.sleep(3)
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass  # Timeout is okay — some pages keep polling
            print(f"Settled on: {page.url}")

        except Exception as e:
            raise Exception(f"MFA handling failed: {str(e)}")

    def _download_csv(self, page: Page, start_date: str = None, end_date: str = None) -> Path:
        """
        Download transactions as CSV
        """
        print("Navigating to download page...")

        try:
            # Navigate to download page — use wait_until domcontentloaded
            # since networkidle can be flaky on eTrade's heavy pages
            page.goto(
                "https://bankus.etrade.com/e/t/ibank/downloadofxtransactions",
                timeout=self.timeout,
                wait_until='domcontentloaded'
            )
            time.sleep(3)

            # Wait for account selector
            page.wait_for_selector('#AcctNum', timeout=self.timeout)

            # Select the checking account
            print("Selecting checking account...")
            page.select_option('#AcctNum', value='2044251052|TELEBANK')
            time.sleep(1)

            # Set date range
            # Convert from YYYY-MM-DD to MM/DD/YY format if provided
            if start_date:
                # Parse YYYY-MM-DD
                date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                formatted_start = date_obj.strftime('%m/%d/%y')
            else:
                # Default to 85 days ago (eTrade enforces a 3-month/~90-day max)
                formatted_start = (datetime.now() - timedelta(days=85)).strftime('%m/%d/%y')

            if end_date:
                date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                formatted_end = date_obj.strftime('%m/%d/%y')
            else:
                # Default to today
                formatted_end = datetime.now().strftime('%m/%d/%y')

            print(f"Setting date range: {formatted_start} to {formatted_end}")
            page.fill('#FromDate', formatted_start)
            page.fill('#ToDate', formatted_end)
            time.sleep(1)

            # Click download button and wait for file
            print("Downloading CSV...")
            with page.expect_download(timeout=60000) as download_info:
                page.click('button:has-text("Download")')

            download = download_info.value

            # Save the downloaded file
            timestamp = int(time.time())
            csv_filename = f"etrade_transactions_{timestamp}.csv"
            csv_path = self.download_dir / csv_filename

            download.save_as(str(csv_path))

            print(f"CSV downloaded: {csv_path}")
            return csv_path

        except Exception as e:
            raise Exception(f"CSV download failed: {str(e)}")

    def test_selectors(self):
        """
        Interactive mode to help identify correct selectors

        This method will pause at each step to allow manual inspection
        """
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.BROWSER_PROFILE_DIR),
                headless=False,
                viewport={'width': 1920, 'height': 1080},
            )
            page = context.new_page()

            print("\n=== eTrade Selector Test Mode ===")
            print("This will help you identify the correct selectors for your eTrade account\n")

            try:
                page.goto("https://us.etrade.com/login", timeout=self.timeout)
                input("Press Enter after the login page loads...")

                print("\nInspect the page and identify:")
                print("1. Username input selector")
                print("2. Password input selector")
                print("3. Login button selector")
                username_selector = input("\nEnter username selector: ")
                password_selector = input("Enter password selector: ")
                login_button_selector = input("Enter login button selector: ")

                page.fill(username_selector, self.username)
                page.fill(password_selector, self.password)
                page.click(login_button_selector)

                input("\nPress Enter after login completes...")

                print("\nNavigate to your checking account and transactions")
                input("Press Enter when you're on the transactions page...")

                print("\nInspect the page and identify the download/export button")
                download_selector = input("Enter download button selector: ")

                print(f"\n=== Selectors Identified ===")
                print(f"Username: {username_selector}")
                print(f"Password: {password_selector}")
                print(f"Login Button: {login_button_selector}")
                print(f"Download Button: {download_selector}")
                print("\nUpdate these selectors in the scraper.py file")

            finally:
                input("\nPress Enter to close browser...")
                context.close()


if __name__ == "__main__":
    """
    Run this script directly to test the scraper or identify selectors
    """
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run in test mode to identify selectors
        scraper = ETradeScraper()
        scraper.test_selectors()
    else:
        # Run normal download
        scraper = ETradeScraper()
        csv_path = scraper.download_transactions()
        print(f"\nDownload complete: {csv_path}")
