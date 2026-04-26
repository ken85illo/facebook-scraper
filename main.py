import os
import random
import subprocess
import sys
import time
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class FacebookScraper:
    def __init__(
        self,
        email: str,
        password: str,
        limit_per_post: int | None = None,
        overall_limit: int = 100,
    ):
        self.email: str = email
        self.password: str = password
        self.driver: WebDriver | None = None
        self.limit_per_post: int | None = limit_per_post
        self.overall_limit: int = overall_limit
        self._posts_links: set[str] = set()
        self._post_id: int = 0

    def initialize_driver(self):
        options = Options()
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)

        self.driver = webdriver.Firefox(options=options)
        print("Opening firefox browser...")
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

    def read_comments_csv(self, filepath: str):
        try:
            df = pd.read_csv(filepath)
            comments: set[tuple[int | datetime | str | None, ...]] = set(
                df.itertuples(index=False, name=None)
            )
            return comments
        except Exception:
            return set[tuple[int | datetime | str | None, ...]]()

    def read_posts_csv(self, filepath: str):
        try:
            df = pd.read_csv(filepath)
            self._posts_links = set(df["Post Link"])

            posts: set[tuple[int, str]] = set(
                df.itertuples(index=False, name=None)
            )
            return posts
        except Exception:
            return set[tuple[int, str]]()

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

        # Wait for the element to be clickable
        element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(element)
        )

        # Move mouse to element before clicking to simulate human behavior
        (
            webdriver.ActionChains(self.driver)
            .move_to_element(element)
            .pause(random.uniform(0.2, 0.4))
            .perform()
        )
        self.driver.execute_script("arguments[0].click();", element)

    def hover_elem(self, element: WebElement):
        if not self.driver:
            return

        (webdriver.ActionChains(self.driver).move_to_element(element).perform())

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

        comment_content = ""

        for comment_body in comment_bodies:
            comment_tag = comment_body.get_attribute("outerHTML")

            if not comment_tag:
                break

            # TODO: Fix the inner comment not getting the full text when it has new line (done)
            comment_content += (
                BeautifulSoup(comment_tag, "html.parser").get_text(strip=True)
                + " "
            )

        return comment_content.strip()

    # TODO: Implement the extraction of date and time per comment (done)
    def _extract_single_comment_date(self, article: WebElement):
        if not self.driver:
            return ""

        # Get the date link <a> tag
        date_link = article.find_elements(
            By.CSS_SELECTOR, "a[role='link']:not([aria-hidden])"
        )

        if not date_link:
            return

        self.scroll_into_view(date_link[-1])
        self.hover_elem(date_link[-1])

        date_tooltip = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[role='tooltip']")
            )
        )

        date_source = date_tooltip.get_attribute("outerHTML")

        if not date_source:
            return

        date_content = BeautifulSoup(date_source, "html.parser").find("span")

        if not date_content:
            return

        # Extract content and put it into a date time object
        format_str = "%A, %B %d, %Y at %I:%M %p"
        dt_object = datetime.strptime(
            date_content.get_text(strip=True), format_str
        )

        return dt_object

    # TODO: Implement the extraction of number of reactions per commment (done)
    def _extract_single_comment_reactions(self, article: WebElement):
        if not self.driver:
            return

        # Reactions: like, love, care, laugh, shock, cry, and angry (7 total)
        reactions = {
            "Like": "0",
            "Love": "0",
            "Care": "0",
            "Haha": "0",
            "Wow": "0",
            "Sad": "0",
            "Angry": "0",
        }

        try:
            # Check if the element has see reaction button (if it has not return the empty reactions)
            comment_reaction_btn = article.find_element(
                By.CSS_SELECTOR, "div[aria-label$='see who reacted to this']"
            )
            self.click_elem(comment_reaction_btn)
        except Exception:
            return tuple(reactions.values())

        # Check if the reaction modal is loaded
        dialog_elem = WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    'div[role="dialog"][aria-labelledby^="_r_"][aria-labelledby$="_"]:has(div[aria-label^="Show"][aria-selected])',
                )
            )
        )

        try:
            # Click the "More" tab of the dialog if its present
            more_btn = dialog_elem.find_element(
                By.CSS_SELECTOR, "div[aria-haspopup]"
            )

            self.click_elem(more_btn)
        except Exception:
            pass

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        for label in list(reactions):
            reaction_elem = soup.select_one(
                f"div[aria-label^='Show'][aria-label$='who reacted with {label}']"
            )

            if not reaction_elem:
                continue

            reaction_value = reaction_elem.select_one("span[dir='auto']")

            if not reaction_value:
                continue

            reactions[label] = reaction_value.get_text(strip=True)

        close_btn = dialog_elem.find_element(
            By.CSS_SELECTOR, "div[aria-label='Close']"
        )
        self.click_elem(close_btn)

        return tuple(reactions.values())

    def extract_comment_articles(
        self,
        dialog_elem: WebElement,
        comments: set[tuple[int | datetime | str | None, ...]],
    ):
        if not self.driver:
            return

        # Checheck natin kung yung naload na comment is mas marami kapag nagscroll tayo pababa
        previous_len = -1
        current_index = 0

        time.sleep(5)

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
                # Scroll sa view ng comment para magload yung mga proceeding
                self.scroll_into_view(article)

                date = self._extract_single_comment_date(article)
                inner_comment = self._extract_single_comment_text(article)
                reactions = self._extract_single_comment_reactions(article)

                if inner_comment and reactions:
                    comments.add(
                        (self._post_id, date, inner_comment, *reactions)
                    )

                current_index += 1

                # If lumagpas na sa max return na
                if len(comments) >= self.overall_limit or (
                    self.limit_per_post
                    and current_index + 1 > self.limit_per_post
                ):
                    return

            previous_len = current_len

    def extract_comments_with_bs(self):
        # Posts id and link
        posts: set[tuple[int, str]] = set()

        # Post id, comment content and 7 reactions (9 total)
        comments: set[tuple[int | datetime | str | None, ...]] = set()

        if not self.driver:
            return posts, comments

        try:
            # Wait until the posts are loaded
            _ = WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[aria-label='Leave a comment']")
                )
            )
            time.sleep(3)

            # Checheck natin kung yung naload na comment button is mas marami kapag nagscroll tayo pababa
            previous_len = -1
            current_index = 0

            while True:
                time.sleep(1)
                # Query all the comment buttons
                all_comment_btns = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[aria-label='Leave a comment']"
                )

                current_len = len(all_comment_btns)
                if current_len <= previous_len:
                    break

                for comment_btn in all_comment_btns[current_index:]:
                    if len(comments) >= self.overall_limit:
                        return posts, comments

                    if not comment_btn.text.strip():
                        continue

                    # Scroll down para magload yung mga proceeding posts
                    self.scroll_into_view(comment_btn)
                    self.click_elem(comment_btn)

                    # Wait until the post modal pops up
                    dialog_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                'div[role="dialog"][aria-labelledby^="_r_"][aria-labelledby$="_"]',
                            )
                        )
                    )

                    close_btn = dialog_elem.find_element(
                        By.CSS_SELECTOR, "div[aria-label='Close']"
                    )

                    # Skip posts links that are already read
                    if self.driver.current_url in self._posts_links:
                        print("Skipping the already read post")
                        self.click_elem(close_btn)
                        current_index += 1
                        continue

                    print("Opened one post!")
                    commment_prev_size = len(comments)

                    self.extract_comment_articles(dialog_elem, comments)

                    added_comments = len(comments) - commment_prev_size

                    if added_comments > 0:
                        print(
                            f"Extracted a total of {len(comments) - commment_prev_size} comments from one post..."
                        )
                        self._post_id += 1
                    else:
                        print("The opened post has no commments!")

                    posts.add((self._post_id, self.driver.current_url))

                    # After maread yung commments close the post modal
                    self.click_elem(close_btn)

                    current_index += 1

                previous_len = current_len

            return posts, comments

        except Exception as e:
            print(f"Error: {e}")
            return posts, comments


if __name__ == "__main__":
    try:
        _, username, password = sys.argv
    except Exception:
        print("Usage: python main.py <username> <password>")
        sys.exit()

    _ = subprocess.run("cls" if os.name == "nt" else "clear", shell=True)

    comments_csv = "facebook_comments.csv"
    posts_csv = "facebook_posts.csv"

    search_terms = ["rice price news"]  # dagdagan niyo nalang dito terms
    urls = [
        f"https://www.facebook.com/search/top?q={term}" for term in search_terms
    ]

    # additional arguments: overall limit and limit per post(bilang ng commments bago lumipat sa ibang post)
    # naka none yung limit per post para magamit dapat iset yung number
    scraper = FacebookScraper(
        username, password, overall_limit=1000, limit_per_post=100
    )

    try:
        # Read first if there is already a csv file
        all_comments: set[tuple[int | datetime | str | None, ...]] = (
            scraper.read_comments_csv(comments_csv)
        )
        all_posts: set[tuple[int, str]] = scraper.read_posts_csv(posts_csv)

        scraper.initialize_driver()
        scraper.login()

        # Extract comments for posts for every search terms
        for url in urls:
            scraper.navigate_to_link(url)
            posts, comments = scraper.extract_comments_with_bs()

            if comments:
                all_comments.update(comments)

            if posts:
                all_posts.update(posts)

        df_posts = pd.DataFrame(
            list(all_posts), columns=["Id", "Post Link"]
        ).sort_values(by="Id")
        df_posts.to_csv(posts_csv, index=False)

        df_comments = pd.DataFrame(
            list(all_comments),
            columns=[
                "Id",
                "Date",
                "Comments",
                "Like",
                "Love",
                "Care",
                "Laugh",
                "Shock",
                "Cry",
                "Angry",
            ],
        ).sort_values(by="Date")
        df_comments.to_csv(comments_csv, index=False)

        print("Scrape results are written in facebook_comments.csv")

    finally:
        scraper.close()
