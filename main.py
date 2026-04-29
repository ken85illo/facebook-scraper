import getpass
import os
import random
import subprocess
import sys
import time
import traceback
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

import requests

SUPABASE_URL = "https://eyzezxuxupjgtfsghtcu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV5emV6eHV4dXBqZ3Rmc2dodGN1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NDQ1NDUsImV4cCI6MjA5MzAyMDU0NX0.xSRbwmINoeedWtDKjs8bkneRWXGzz-z1_4X3M3ijerw"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation,resolution=merge-duplicates"
}

def post_exists(link: str) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/facebook_posts"

    params = {
        "select": "post_id",
        "post_link": f"eq.{link}",
        "limit": "1"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("Error:", response.text)
        return False

    data = response.json()

    return len(data) > 0

def insert_post(post) -> int:
    url = f"{SUPABASE_URL}/rest/v1/facebook_posts"

    response = requests.post(url, json=post, headers=headers)

    if response.status_code in (200, 201):
        print("Inserted:", post["post_link"])

        data = response.json()

        return data[0]["post_id"]

    else:
        print("Error:", response.text)
    
def insert_comment(comment, post_id):
    comment["post_id"] = post_id;

    url = f"{SUPABASE_URL}/rest/v1/facebook_comments"

    response = requests.post(url, json=comment, headers=headers)
    
    if response.status_code in (200, 201):
        print("Inserted:", comment)
    else:
        print("Error:", response.text)

# pyright: reportUnknownMemberType = false
class Col:
    BLUE: str = "\033[94m"
    CYAN: str = "\033[96m"
    GREEN: str = "\033[92m"
    YELLOW: str = "\033[93m"
    RED: str = "\033[91m"
    BOLD: str = "\033[1m"
    END: str = "\033[0m"


def log_info(msg: str):
    print(f"{Col.BLUE}[INFO]{Col.END} {msg}")


def log_success(msg: str):
    print(f"{Col.GREEN}[SUCCESS]{Col.END} {msg}")


def log_warn(msg: str):
    print(f"{Col.YELLOW}[WARN]{Col.END} {msg}")


def log_error(msg: str):
    print(f"{Col.RED}[ERROR]{Col.END} {msg}")


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
        log_info(f"Opening {Col.BOLD}Firefox{Col.END} browser...")
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

    def read_posts_csv(self, filepath: str):
        if os.path.isfile(filepath):
            df = pd.read_csv(filepath)

            if "Post Link" in df.columns:
                self._posts_links = set(df["Post Link"])

            if "Id" in df.columns:
                last_index = int(df["Id"].values[-1]) + 1
                self._post_id = last_index

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

    def hover_elem(self, element: WebElement):
        if not self.driver:
            return

        (webdriver.ActionChains(self.driver).move_to_element(element).perform())

    def login(self):
        if not self.driver:
            return

        self.driver.get("https://www.facebook.com/login")
        log_info(f"Logging in as: {Col.CYAN}{self.email}{Col.END}...")

        time.sleep(3)

        # Enter email
        email_input = WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        self.simulate_human_typing(email_input, self.email)

        # Enter password
        password_input = WebDriverWait(self.driver, 300).until(
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

        log_success("Login successful!")
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

        date_tooltip = WebDriverWait(self.driver, 300).until(
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

    def _write_csv(
        self,
        path: str,
        data: set[tuple[int | datetime | str | None, ...]]
        | set[tuple[int, str]],
        sort_col: str,
        columns: list[str],
        datetime: bool = False,
    ):
        df_new = pd.DataFrame(list(data), columns=columns).sort_values(
            by=sort_col
        )

        if os.path.isfile(path):
            df_current = pd.read_csv(path)

            df_new[sort_col] = (
                pd.to_datetime(df_new[sort_col])
                if datetime
                else df_new[sort_col]
            )
            df_current[sort_col] = (
                pd.to_datetime(df_current[sort_col])
                if datetime
                else df_current[sort_col]
            )

            df_write = pd.concat([df_new, df_current]).sort_values(by=sort_col)

            df_write.to_csv(path, index=False)

        else:
            df_new.to_csv(path, index=False)

        log_success(f"Appended new data to {Col.CYAN}{path}{Col.END}...")

    def extract_comments_with_bs(self, posts_path: str, comments_path: str):
        # Posts id and link
        posts: set[tuple[int, str]] = set()

        # Post id, comment content and 7 reactions (9 total)
        comments: set[tuple[int | datetime | str | None, ...]] = set()

        if not self.driver:
            return

        def write_csv_files():
            self._write_csv(posts_path, posts, "Id", ["Id", "Post Link"])
            self._write_csv(
                comments_path,
                comments,
                "Date",
                [
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
                datetime=True,
            )
            posts.clear()
            comments.clear()

        try:
            # Wait until the posts are loaded
            _ = WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[aria-label='Leave a comment']")
                )
            )

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
                        write_csv_files()
                        return

                    if not comment_btn.text.strip():
                        continue

                    # Scroll down para magload yung mga proceeding posts
                    self.scroll_into_view(comment_btn)
                    self.click_elem(comment_btn)

                    # Wait until the post modal pops up
                    dialog_elem = WebDriverWait(self.driver, 300).until(
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

                    # >>> Binago ko ang condition
                    # Skip posts links that are already read
                    if post_exists(self.driver.current_url):
                        log_warn(
                            f"Skipping already read post: {Col.CYAN}{self.driver.current_url}{Col.END}"
                        )
                        self.click_elem(close_btn)
                        current_index += 1
                        continue

                    log_info(
                        f"Processing post {Col.BOLD}#{self._post_id}{Col.END}..."
                    )
                    commment_prev_size = len(comments)

                    self.extract_comment_articles(dialog_elem, comments)

                    added_comments = len(comments) - commment_prev_size

                    if added_comments > 0:
                        log_success(
                            f"Extracted {Col.BOLD}{added_comments}{Col.END} comments from this post."
                        )
                    else:
                        log_warn("The opened post has no comments!")

                    post_json = {
                        "post_link": f"{self.driver.current_url}"
                    }

                    insert_post(post_json)

                    posts.add((self._post_id, self.driver.current_url))
                    self._post_id += 1

                    # After maread yung commments close the post modal
                    self.click_elem(close_btn)

                    write_csv_files()
                    current_index += 1

                previous_len = current_len

        except Exception:
            log_error("An error occurred during extraction:")
            traceback.print_exc()


if __name__ == "__main__":
    _ = subprocess.run("cls" if os.name == "nt" else "clear", shell=True)

    # ======================= INPUT ========================================
    print(f"{Col.BLUE}{Col.BOLD}" + "=" * 50)
    print(" " * 13 + "FACEBOOK COMMENT SCRAPER")
    print("=" * 50 + f"{Col.END}\n")

    username = input(f"{Col.CYAN}Enter Facebook Email/Phone: {Col.END}")
    if not username:
        log_error("Username cannot be empty.")
        sys.exit()

    password = getpass.getpass(
        f"{Col.CYAN}Enter Facebook Password (hidden): {Col.END}", echo_char="*"
    )

    print(f"\n{Col.YELLOW}--- Configuration ---{Col.END}")
    target_limit = input("Overall comment limit [Default 1000]: ") or "1000"
    post_limit = input("Limit per post [Default 100]: ") or "100"
    # ======================================================================

    overall_limit = int(target_limit)
    limit_per_post = int(post_limit)

    posts_csv = "facebook_posts.csv"
    comments_csv = "facebook_comments.csv"

    search_terms = ["rice price news"]  # dagdagan niyo nalang dito terms
    urls = [
        f"https://www.facebook.com/search/top?q={term}&filters=eyJycF9jcmVhdGlvbl90aW1lOjAiOiJ7XCJuYW1lXCI6XCJjcmVhdGlvbl90aW1lXCIsXCJhcmdzXCI6XCJ7XFxcInN0YXJ0X3llYXJcXFwiOlxcXCIyMDIwXFxcIixcXFwic3RhcnRfbW9udGhcXFwiOlxcXCIyMDIwLTFcXFwiLFxcXCJlbmRfeWVhclxcXCI6XFxcIjIwMjBcXFwiLFxcXCJlbmRfbW9udGhcXFwiOlxcXCIyMDIwLTEyXFxcIixcXFwic3RhcnRfZGF5XFxcIjpcXFwiMjAyMC0xLTFcXFwiLFxcXCJlbmRfZGF5XFxcIjpcXFwiMjAyMC0xMi0zMVxcXCJ9XCJ9In0%3D"
        for term in search_terms
    ]

    # additional arguments: overall limit and limit per post(bilang ng commments bago lumipat sa ibang post)
    # naka none yung limit per post para magamit dapat iset yung number
    scraper = FacebookScraper(
        username,
        password,
        overall_limit=overall_limit,
        limit_per_post=limit_per_post,
    )

    try:
        # Read first if there is already a csv file
        scraper.read_posts_csv(posts_csv)

        scraper.initialize_driver()
        scraper.login()

        # Extract comments for posts for every search terms
        for url in urls:
            scraper.navigate_to_link(url)
            scraper.extract_comments_with_bs(posts_csv, comments_csv)

        print(f"\n{Col.GREEN}{Col.BOLD}✔ SCRAPING COMPLETE!{Col.END}")
        log_success(f"Results saved to {Col.BOLD}{comments_csv}{Col.END}")

    finally:
        scraper.close()
