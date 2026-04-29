import requests
import datetime

SUPABASE_URL = "https://eyzezxuxupjgtfsghtcu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV5emV6eHV4dXBqZ3Rmc2dodGN1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NDQ1NDUsImV4cCI6MjA5MzAyMDU0NX0.xSRbwmINoeedWtDKjs8bkneRWXGzz-z1_4X3M3ijerw"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation,resolution=merge-duplicates"
}

def post_exists(link: str) -> bool:
    TABLE = "facebook_posts"
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"

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
    TABLE = "facebook_posts"
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    response = requests.post(url, json=post, headers=headers)

    if response.status_code in (200, 201):

        data = response.json()

        return data[0]["post_id"]

    else:
        print("Error:", response.text)


def insert_comment(comment: list[dict]):
    TABLE = "facebook_comments"
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    response = requests.post(url, json=comment, headers=headers)
    
    if response.status_code in (200, 201):
        print("Inserted:", comment)
    else:
        print("Error:", response.text)

if __name__ == "__main__":

    post_json = {
        "post_link": "test123"
    }
    
    comments: set[tuple[int | datetime | str | None, ...]] = set()

    comments = {
        (1, "03/24/2026", "Hello 1", 0, 0, 10, 0, 0, 0, 0),
        (1, "02/14/2027", "Hello 2", 10, 0, 0, 0, 0, 0, 0),
        (1, "12/10/2026", "Hello 3", 0, 10, 0, 0, 0, 0, 0),
    }

    comments_json = []

    for comment in comments:
        comments_json.append({
            "date": comment[1],
            "comments": comment[2],
            "like": comment[3],
            "love": comment[4],
            "care": comment[5],
            "laugh": comment[6],
            "shock": comment[7],
            "cry": comment[8],
            "angry": comment[9]
        })

    insert_comment(comments_json)

    res = insert_post(post_json)

    print(f"post id: {res}")