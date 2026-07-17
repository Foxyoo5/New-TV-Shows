import requests
import datetime
import xml.etree.ElementTree as ET
from email.utils import format_datetime

# ----------------------------
# CONFIG
# ----------------------------

API_KEY = "YOUR_TMDB_API_KEY"

LANGUAGE = "en-GB"

NETWORKS = "213|2739|2552|1024|49"
# Netflix | Disney+ | Apple TV+ | Prime Video | MGM+

DAYS_BACK = 120
MAX_RESULTS = 30

today = datetime.date.today()
start_date = today - datetime.timedelta(days=DAYS_BACK)

BASE_URL = "https://api.themoviedb.org/3/discover/tv"

# ----------------------------
# Helper
# ----------------------------

def fetch(params):
    results = []
    page = 1

    while True:
        params["page"] = page

        r = requests.get(
            BASE_URL,
            params=params,
            timeout=30
        )

        r.raise_for_status()

        data = r.json()

        results.extend(data["results"])

        if page >= data["total_pages"] or page >= 3:
            break

        page += 1

    return results


# ----------------------------
# Query 1
# Recent premieres
# ----------------------------

recent = fetch({
    "api_key": API_KEY,
    "language": LANGUAGE,
    "sort_by": "first_air_date.desc",
    "include_adult": "false",
    "include_null_first_air_dates": "false",
    "with_networks": NETWORKS,
    "first_air_date.gte": start_date.isoformat(),
    "first_air_date.lte": today.isoformat(),
    "vote_count.gte": 15,
    "vote_average.gte": 6
})

# ----------------------------
# Query 2
# Popular shows from same networks
# ----------------------------

popular = fetch({
    "api_key": API_KEY,
    "language": LANGUAGE,
    "sort_by": "popularity.desc",
    "include_adult": "false",
    "include_null_first_air_dates": "false",
    "with_networks": NETWORKS,
    "vote_count.gte": 15,
    "vote_average.gte": 6
})

# ----------------------------
# Merge duplicates
# ----------------------------

shows = {}

for show in recent + popular:
    shows[show["id"]] = show

shows = list(shows.values())

# ----------------------------
# Score shows
# ----------------------------

for show in shows:

    first = show.get("first_air_date")

    if first:
        age = (today - datetime.date.fromisoformat(first)).days
    else:
        age = 9999

    popularity = show.get("popularity", 0)
    votes = show.get("vote_count", 0)
    rating = show.get("vote_average", 0)

    score = (
        popularity * 2
        + votes * 0.35
        + rating * 10
        - age * 0.35
    )

    show["score"] = score

shows.sort(
    key=lambda x: x["score"],
    reverse=True
)

shows = shows[:MAX_RESULTS]

# ----------------------------
# Build RSS
# ----------------------------

rss = ET.Element("rss")
rss.set("version", "2.0")

channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "New TV Shows"
ET.SubElement(channel, "link").text = "https://www.themoviedb.org"
ET.SubElement(channel, "description").text = "Recently released TV shows"

ET.SubElement(channel, "lastBuildDate").text = format_datetime(
    datetime.datetime.now(datetime.timezone.utc)
)

for show in shows:

    item = ET.SubElement(channel, "item")

    ET.SubElement(item, "title").text = show["name"]

    ET.SubElement(
        item,
        "link"
    ).text = f"https://www.themoviedb.org/tv/{show['id']}"

    ET.SubElement(
        item,
        "guid"
    ).text = str(show["id"])

    air = show.get("first_air_date", "")

    overview = show.get("overview", "")

    poster = ""

    if show.get("poster_path"):
        poster = (
            "https://image.tmdb.org/t/p/w780"
            + show["poster_path"]
        )

    description = f"""
<![CDATA[
<img src="{poster}" /><br/>
<b>First Air Date:</b> {air}<br/><br/>
{overview}
]]>
"""

    ET.SubElement(
        item,
        "description"
    ).text = description

tree = ET.ElementTree(rss)
tree.write(
    "rss.xml",
    encoding="utf-8",
    xml_declaration=True
)

print(f"Generated rss.xml with {len(shows)} shows.")