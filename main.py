import random
import time

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


# pyright: reportUnknownMemberType=false
class FacebookScraper:
    def __init__(
        self,
        email: str,
        password: str,
        limit_per_post: int | None = 100,
        overall_limit: int = 100,
    ):
        self.email: str = email
        self.password: str = password
        self.driver: WebDriver | None = None
        self.limit_per_post: int | None = limit_per_post
        self.overall_limit: int = overall_limit

    def initialize_driver(self):
        options = Options()

        # 1. Remove the "automated testing" notification
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # 2. Disable blink features that detect automation
        options.add_argument('--disable-blink-features=AutomationControlled')

        # 3. Set a real user-agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0')

        # 4. Additional stealth arguments
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--start-maximized')

        self.driver = webdriver.Edge(options=options)
        print("Opening edge browser...")
        time.sleep(3)

    def close(self):
        if self.driver:
            self.driver.quit()

    def navigate_to_link(self, url: str):
        if self.driver:
            self.driver.get(url)
            time.sleep(4)

    def simulate_human_typing(self, element: WebElement, text: str):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
            if random.random() < 0.1:
                time.sleep(random.uniform(0.3, 0.7))

    def scroll_into_view(self, element: WebElement):
        if self.driver:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });",
                element,
            )
            time.sleep(2)

    def click_elem(self, element: WebElement):
        if not self.driver:
            return
        # Move mouse to element before clicking to simulate human behavior
        (
            webdriver.ActionChains(self.driver)
            .move_to_element(element)
            .pause(random.uniform(0.2, 0.4))
            .perform()
        )
        self.driver.execute_script("arguments[0].click();", element)

    def login(self):
        if not self.driver:
            return

        self.driver.get("https://www.facebook.com/login")
        print(f"Sign up with email {self.email}...")

        time.sleep(3)

        # Enter email
        email_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        self.simulate_human_typing(email_input, self.email)

        # Enter password
        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "pass"))
        )
        self.simulate_human_typing(password_input, self.password)

        login_button = self.driver.find_element(
            By.CSS_SELECTOR, "div[aria-label='Log In']"
        )
        self.click_elem(login_button)

        # Wait for the home page to load
        _ = WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[aria-label='Facebook']")
            )
        )

        print("Sign up done!")
        time.sleep(5)

    def _extract_single_comment_text(self, article: WebElement):
        # Query the comment inside the article div

        comment_bodies = article.find_elements(
            By.CSS_SELECTOR, "div[dir='auto']"
        )

        if not comment_bodies:
            return

        comment_body = comment_bodies[-1]
        comment_tag = comment_body.get_attribute("outerHTML")

        if not comment_tag:
            return ""

        inner_comment = BeautifulSoup(comment_tag, "html.parser").get_text(
            separator=" ", strip=True
        )

        # Scroll sa view ng comment para magload yung mga proceeding
        self.scroll_into_view(comment_body)
        return inner_comment

    def extract_comment_articles(
        self, dialog_elem: WebElement, comments: set[str]
    ):
        if not self.driver:
            return

        # Wait for the comments to load
        _ = WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "div[role='article'][aria-label^='Comment by']",
                )
            )
        )

        # Checheck natin kung yung naload na comment is mas marami kapag nagscroll tayo pababa
        previous_len = -1
        current_index = 0

        while True:
            # Query all the commment articles (article role and yung label niya nagsisimula sa Comment By...)
            comment_articles = dialog_elem.find_elements(
                By.CSS_SELECTOR, "div[role='article'][aria-label^='Comment by']"
            )

            current_len = len(comment_articles)
            if current_len <= previous_len:
                break

            # Skip yung mga previously na read na comments (current_index)
            for article in comment_articles[current_index:]:
                inner_comment = self._extract_single_comment_text(article)

                if inner_comment:
                    comments.add(inner_comment)

                current_index += 1

                # If lumagpas na sa max return na
                if len(comments) >= self.overall_limit or (
                    self.limit_per_post
                    and current_index + 1 > self.limit_per_post
                ):
                    return

            previous_len = current_len

    def extract_comments_with_bs(self):
        if not self.driver:
            return

        # Wait until the posts are loaded
        _ = WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[aria-label='Leave a comment']")
            )
        )

        # Checheck natin kung yung naload na comment button is mas marami kapag nagscroll tayo pababa
        previous_len = -1
        current_index = 0
        comments: set[str] = set()

        while True:
            time.sleep(3)
            # Query all the comment buttons
            all_comment_btns = self.driver.find_elements(
                By.CSS_SELECTOR, "div[aria-label='Leave a comment']"
            )

            current_len = len(all_comment_btns)
            if current_len <= previous_len:
                break

            for comment_btn in all_comment_btns[current_index:]:
                if len(comments) >= self.overall_limit:
                    return comments

                # Scroll down para magload yung mga proceeding posts
                self.scroll_into_view(comment_btn)
                self.click_elem(comment_btn)
                time.sleep(3)

                # Wait until the post modal pops up
                dialog_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            'div[role="dialog"][aria-labelledby^="_r_"][aria-labelledby$="_"]',
                        )
                    )
                )

                print("Opened one post!")
                commment_prev_size = len(comments)

                self.extract_comment_articles(dialog_elem, comments)

                added_comments = len(comments) - commment_prev_size

                if added_comments > 0:
                    print(
                        f"Extracted a total of {len(comments) - commment_prev_size} comments from one post..."
                    )
                else:
                    print("The opened post has no commments!")

                # After maread yung commments close the post modal
                close_btn = dialog_elem.find_element(
                    By.CSS_SELECTOR, "div[aria-label='Close']"
                )
                self.click_elem(close_btn)

                current_index += 1

            previous_len = current_len

        return comments


if __name__ == "__main__":
    search_terms = ["rice news"]  # dagdagan niyo nalang dito terms
    urls = [
        f"https://www.facebook.com/search/top?q={term}" for term in search_terms
    ]

    # additional arguments: overall limit and limit per post(bilang ng commments bago lumipat sa ibang post)
    # naka none yung limit per post para magamit dapat iset yung number
    scraper = FacebookScraper("username", "password")

    try:
        scraper.initialize_driver()
        scraper.login()

        all_comments: set[str] = set()

        # Extract comments for posts for every search terms
        for url in urls:
            scraper.navigate_to_link(url)
            comments = scraper.extract_comments_with_bs()

            if comments:
                all_comments.update(comments)

        if all_comments:
            df = pd.DataFrame(
                {"comments": [comment for comment in all_comments]}
            )
            df.to_csv("facebook_comments.csv")

    finally:
        scraper.close()
