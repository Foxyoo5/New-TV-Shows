import os
import html
import datetime
import requests

API_KEY = os.environ["TMDB_API_KEY"]
TODAY = datetime.date.today().isoformat()
NETWORKS = "213|2739|6219|2552|1024"

params = {
    "api_key": API_KEY,
    "air_date.gte": TODAY,
    "air_date.lte": TODAY,
    "with_networks": NETWORKS,
    "with_original_language": "en",
    "language": "en-US",
    "sort_by": "first_air_date.desc",
}

resp = requests.get("https://api.themoviedb.org/3/discover/tv", params=params, timeout=30)
resp.raise_for_status()
shows = resp.json().get("results", [])

now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
items = []

for show in shows:
    title = html.escape(show.get("name", "Untitled"))
    show_id = show.get("id")
    link = "https://www.themoviedb.org/tv/" + str(show_id)
    poster_path = show.get("poster_path")
    overview = html.escape(show.get("overview", "") or "")

    if poster_path:
        poster_url = "https://image.tmdb.org/t/p/w500" + poster_path
        img_tag = "<img src=" + chr(34) + poster_url + chr(34) + "/><br/>"
        desc_body = img_tag + overview
        enclosure = "<enclosure url=" + chr(34) + poster_url + chr(34) + " type=" + chr(34) + "image/jpeg" + chr(34) + "/>"
    else:
        desc_body = overview
        enclosure = ""

    desc = "
