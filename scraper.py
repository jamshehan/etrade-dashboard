from playwright.sync_api import sync_playwright, Page, Browser
from pathlib import Path
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
            browser = playwright.chromium.launch(headless=self.headless)

            # Configure browser context with download directory
            context = browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080}
            )

            page = context.new_page()

            try:
                print("Navigating to eTrade login page...")
                # Navigate to eTrade login
                # TODO: Replace with actual eTrade login URL
                page.goto("https://us.etrade.com/login", timeout=self.timeout)

                # Wait for page to load
                time.sleep(2)

                # Perform login
                self._login(page)

                # Navigate to checking account
                self._navigate_to_checking(page)

                # Download CSV
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

        NOTE: This method needs to be customized based on actual eTrade login flow
        """
        print("Logging in...")

        try:
            # TODO: Replace these selectors with actual eTrade selectors
            # You can find selectors by inspecting the eTrade login page

            # Example selectors (THESE WILL NEED TO BE UPDATED):
            # Wait for username field
            page.wait_for_selector('input[name="USER"]', timeout=self.timeout)

            # Fill username
            page.fill('input[name="USER"]', self.username)

            # Fill password
            page.fill('input[name="PASSWORD"]', self.password)

            # Click login button
            page.click('button[type="submit"]')

            # Wait for login to complete
            # TODO: Replace with actual selector that appears after successful login
            page.wait_for_selector('text=Accounts', timeout=self.timeout)

            print("Login successful")

            # Handle potential 2FA or security questions
            # TODO: Add 2FA handling if needed
            time.sleep(3)

        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    def _navigate_to_checking(self, page: Page):
        """
        Navigate to checking account transactions page

        NOTE: This method needs to be customized based on actual eTrade navigation
        """
        print("Navigating to checking account...")

        try:
            # TODO: Replace with actual navigation steps for eTrade

            # Example navigation (THESE WILL NEED TO BE UPDATED):
            # Click on checking account link
            page.click('text=Checking')

            # Wait for transactions to load
            page.wait_for_selector('text=Transactions', timeout=self.timeout)

            print("Reached checking account page")
            time.sleep(2)

        except Exception as e:
            raise Exception(f"Navigation failed: {str(e)}")

    def _download_csv(self, page: Page, start_date: str = None, end_date: str = None) -> Path:
        """
        Download transactions as CSV

        NOTE: This method needs to be customized based on actual eTrade download flow
        """
        print("Downloading CSV...")

        try:
            # TODO: Replace with actual eTrade CSV download steps

            # Example download flow (THESE WILL NEED TO BE UPDATED):

            # 1. If date range needed, set filters
            if start_date or end_date:
                # Click date filter
                page.click('button:has-text("Date Range")')
                time.sleep(1)

                if start_date:
                    page.fill('input[name="startDate"]', start_date)

                if end_date:
                    page.fill('input[name="endDate"]', end_date)

                # Apply filter
                page.click('button:has-text("Apply")')
                time.sleep(2)

            # 2. Click download/export button
            page.click('button:has-text("Download")')
            time.sleep(1)

            # 3. Select CSV format
            page.click('text=CSV')

            # 4. Wait for download to start
            with page.expect_download() as download_info:
                page.click('button:has-text("Export")')

            download = download_info.value

            # 5. Save the downloaded file
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
