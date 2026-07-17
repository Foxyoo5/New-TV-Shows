import os
import requests
import datetime
import time
import xml.etree.ElementTree as ET
from email.utils import format_datetime


# ==========================================================
# CONFIGURATION
# ==========================================================

API_KEY = os.environ["TMDB_API_KEY"]

LANGUAGE = "en-GB"

MAX_SHOWS = 5

TODAY = datetime.date.today()

# How far back we consider a show "new"
DAYS_BACK = 45

CUTOFF = (
    TODAY - datetime.timedelta(days=DAYS_BACK)
).isoformat()

TODAY_STR = TODAY.isoformat()


# TMDB network IDs
NETWORKS = {
    "Netflix": 213,
    "Disney+": 2739,
    "Apple TV+": 2552,
    "Prime Video": 1024,
    "MGM+": 49,
}


BASE_URL = "https://api.themoviedb.org/3"


# ==========================================================
# API HELPERS
# ==========================================================

session = requests.Session()


def tmdb_get(endpoint, params=None):

    if params is None:
        params = {}

    params["api_key"] = API_KEY
    params["language"] = LANGUAGE

    url = BASE_URL + endpoint

    for attempt in range(3):

        try:

            response = session.get(
                url,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            return response.json()

        except Exception as e:

            print(
                f"TMDB error on {endpoint}: {e}"
            )

            if attempt < 2:
                time.sleep(3)

            else:
                return {}


# ==========================================================
# DISCOVER SHOWS
# ==========================================================

def discover_network(network_id):

    print(
        f"Fetching network {network_id}"
    )

    shows = []

    for page in range(1, 4):

        data = tmdb_get(
            "/discover/tv",
            {
                "page": page,
                "include_adult": "false",
                "include_null_first_air_dates": "false",
                "sort_by": "popularity.desc",

                "with_networks": network_id,

                "first_air_date.gte": CUTOFF,
                "first_air_date.lte": TODAY_STR,

                "vote_count.gte": 20,
                "vote_average.gte": 6
            }
        )


        results = data.get(
            "results",
            []
        )

        shows.extend(results)


        if len(results) < 20:
            break


    print(
        f"Found {len(shows)} shows"
    )

    return shows



# ==========================================================
# GET SHOW DETAILS
# ==========================================================

def get_show_details(show_id):

    return tmdb_get(
        f"/tv/{show_id}"
    )



# ==========================================================
# CLEAN AND SCORE RESULTS
# ==========================================================

def calculate_score(show):

    first_air = show.get(
        "first_air_date"
    )


    if first_air:

        try:
            age = (
                TODAY -
                datetime.date.fromisoformat(first_air)
            ).days

        except:
            age = 999

    else:
        age = 999



    popularity = show.get(
        "popularity",
        0
    )

    votes = show.get(
        "vote_count",
        0
    )

    rating = show.get(
        "vote_average",
        0
    )


    return (
        popularity * 2
        +
        votes * 0.4
        +
        rating * 10
        -
        age * 0.5
    )



def clean_results(all_shows):

    cleaned = {}

    for show, network_name in all_shows:


        show_id = show.get(
            "id"
        )

        if not show_id:
            continue


        if show_id not in cleaned:

            show["matched_network"] = network_name

            cleaned[show_id] = show



    final = list(
        cleaned.values()
    )


    for show in final:

        show["score"] = calculate_score(show)



    final.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    return final
    # ==========================================================
# BALANCE RESULTS BETWEEN SERVICES
# ==========================================================

def select_top_shows(shows):

    selected = []

    service_limits = {
        "Netflix": 2,
        "Disney+": 1,
        "Apple TV+": 1,
        "Prime Video": 1,
        "MGM+": 1
    }


    service_counts = {
        key: 0
        for key in service_limits
    }


    for show in shows:

        service = show.get(
            "matched_network"
        )


        if service in service_limits:

            if (
                service_counts[service]
                <
                service_limits[service]
            ):

                selected.append(show)

                service_counts[service] += 1



        if len(selected) >= MAX_SHOWS:
            break



    return selected



# ==========================================================
# RSS GENERATION
# ==========================================================

def create_rss(shows):

    rss = ET.Element(
        "rss",
        {
            "version": "2.0"
        }
    )


    channel = ET.SubElement(
        rss,
        "channel"
    )


    ET.SubElement(
        channel,
        "title"
    ).text = "New Streaming TV Shows"


    ET.SubElement(
        channel,
        "link"
    ).text = "https://www.themoviedb.org"


    ET.SubElement(
        channel,
        "description"
    ).text = (
        "Latest notable TV releases "
        "from major streaming services"
    )


    ET.SubElement(
        channel,
        "lastBuildDate"
    ).text = format_datetime(
        datetime.datetime.now(
            datetime.timezone.utc
        )
    )


    for show in shows:

        item = ET.SubElement(
            channel,
            "item"
        )


        title = show.get(
            "name",
            "Unknown"
        )


        poster = ""

        if show.get(
            "poster_path"
        ):

            poster = (
                "https://image.tmdb.org/t/p/original"
                +
                show["poster_path"]
            )


        overview = show.get(
            "overview",
            ""
        )


        network = show.get(
            "matched_network",
            ""
        )


        description = f"""
<![CDATA[
<img src="{poster}" /><br/>
<b>Platform:</b> {network}<br/>
<b>First Air Date:</b> {show.get('first_air_date','')}<br/><br/>
{overview}
]]>
"""


        ET.SubElement(
            item,
            "title"
        ).text = title


        ET.SubElement(
            item,
            "link"
        ).text = (
            f"https://www.themoviedb.org/tv/{show['id']}"
        )


        ET.SubElement(
            item,
            "guid"
        ).text = str(
            show["id"]
        )


        ET.SubElement(
            item,
            "description"
        ).text = description



    tree = ET.ElementTree(
        rss
    )


    tree.write(
        "rss.xml",
        encoding="utf-8",
        xml_declaration=True
    )


    print(
        f"Created rss.xml with {len(shows)} shows"
    )



# ==========================================================
# MAIN
# ==========================================================

def main():

    print(
        "Starting TMDB TV feed generation..."
    )


    collected = []


    for network_name, network_id in NETWORKS.items():

        results = discover_network(
            network_id
        )


        for show in results:

            collected.append(
                (
                    show,
                    network_name
                )
            )



    print(
        f"Total collected: {len(collected)}"
    )


    cleaned = clean_results(
        collected
    )


    print(
        "Top ranked shows:"
    )


    for show in cleaned[:10]:

        print(
            show["name"],
            "-",
            show.get(
                "matched_network"
            ),
            "- score:",
            round(
                show["score"],
                2
            )
        )



    selected = select_top_shows(
        cleaned
    )


    print(
        "Selected:"
    )


    for show in selected:

        print(
            show["name"],
            "(",
            show.get(
                "matched_network"
            ),
            ")"
        )



    create_rss(
        selected
    )



if __name__ == "__main__":

    main()