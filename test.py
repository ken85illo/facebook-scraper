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
        print("Inserted:", post["post_link"])

        data = response.json()

        return data[0]["post_id"]

    else:
        print("Error:", response.text)
    
def insert_comment(comment, post_id):
    comment["post_id"] = post_id;
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
    
    comment_json = {
        "date": "04/29/2026",
        "comments": "Hello pangga"
    }
    
    if(not post_exists(post_json["post_link"])):

        res = insert_post(post_json)
    
        print(f"post id: {res}")


        insert_comment(comment_json, res)

    else:
        print(f"post already exists: {post_json["post_link"]}")
    
