from playwright.sync_api import sync_playwright, Page, Browser
from pathlib import Path
from datetime import datetime, timedelta
import time
import config


class ETradeScraper:
    """
    Web scraper for eTrade checking account transactions

    NOTE: This is a template that will need to be customized based on
    the actual eTrade website structure and selectors.
    """

    def __init__(self, username: str = None, password: str = None):
        self.username = username or config.ETRADE_USERNAME
        self.password = password or config.ETRADE_PASSWORD
        self.download_dir = config.DOWNLOAD_DIR
        self.headless = config.HEADLESS
        self.timeout = config.SCRAPER_TIMEOUT

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
            # Force non-headless for MFA handling
            browser = playwright.chromium.launch(headless=False)

            # Configure browser context with download directory
            context = browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080}
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
                browser.close()

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
            time.sleep(1)

            current_url = page.url
            print(f"Current URL after load: {current_url}")

            # Check if we're on the send OTP page
            if "sendotpcode" in current_url:
                print("MFA required - triggering SMS code...")

                # Wait for the send OTP button to be visible
                page.wait_for_selector('#sendOTPCodeBtn', timeout=self.timeout)
                page.click('#sendOTPCodeBtn')

                print("SMS code requested, waiting for verification page...")

                # Wait for verification code page
                page.wait_for_url("**/verifyotpcode", timeout=self.timeout)
                time.sleep(1)

                print("\n" + "="*60)
                print("MFA CODE REQUIRED")
                print("="*60)
                print("1. Check your phone for the SMS code from eTrade")
                print("2. Enter the code in the browser window that opened")
                print("3. Check the 'Save this device' checkbox to skip MFA next time")
                print("4. Click Submit")
                print("="*60 + "\n")

                # Wait for user to manually enter code and submit
                # We'll wait until we're no longer on the verifyotpcode page
                print("Waiting for MFA submission...")
                try:
                    page.wait_for_url(lambda url: "verifyotpcode" not in url, timeout=120000)  # 2 minutes
                except Exception as e:
                    print(f"Error waiting for URL change: {e}")
                    print(f"Current URL: {page.url}")
                    raise Exception("Timeout or error waiting for MFA submission")

                print("MFA completed successfully")
                time.sleep(3)

            elif "verifyotpcode" in current_url:
                # Already on verification page (shouldn't normally happen)
                print("\n" + "="*60)
                print("MFA CODE REQUIRED")
                print("="*60)
                print("1. Check your phone for the SMS code")
                print("2. Enter the code in the browser window")
                print("3. Check 'Save this device' to skip MFA next time")
                print("4. Click Submit")
                print("="*60 + "\n")

                print("Waiting for MFA submission...")
                try:
                    page.wait_for_url(lambda url: "verifyotpcode" not in url, timeout=120000)  # 2 minutes
                except Exception as e:
                    print(f"Error waiting for URL change: {e}")
                    print(f"Current URL: {page.url}")
                    raise Exception("Timeout or error waiting for MFA submission")

                print("MFA completed successfully")
                time.sleep(3)

            else:
                print(f"No MFA required - device already trusted (URL: {current_url})")

        except Exception as e:
            raise Exception(f"MFA handling failed: {str(e)}")

    def _download_csv(self, page: Page, start_date: str = None, end_date: str = None) -> Path:
        """
        Download transactions as CSV
        """
        print("Navigating to download page...")

        try:
            # Navigate directly to the download page
            page.goto("https://bankus.etrade.com/e/t/ibank/downloadofxtransactions", timeout=self.timeout)
            time.sleep(2)

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
                # Default to 90 days ago
                formatted_start = (datetime.now() - timedelta(days=90)).strftime('%m/%d/%y')

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
            with page.expect_download() as download_info:
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
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
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
                browser.close()


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
