import os
import requests
import datetime
import time
from email.utils import format_datetime

API_KEY = os.environ["TMDB_API_KEY"]
LANGUAGE = "en-GB"
MAX_SHOWS = 5
TODAY = datetime.date.today()
DAYS_BACK = 45
CUTOFF = (TODAY - datetime.timedelta(days=DAYS_BACK)).isoformat()
TODAY_STR = TODAY.isoformat()

NETWORKS = {
    "Netflix": 213,
    "Disney+": 2739,
    "Apple TV+": 2552,
    "Prime Video": 1024,
    "MGM+": 6219,
    "Sky Max": 5237,
}

BASE_URL = "https://api.themoviedb.org/3"
session = requests.Session()


def tmdb_get(endpoint, params=None):
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    params["language"] = LANGUAGE
    url = BASE_URL + endpoint

    for attempt in range(3):
        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print("TMDB error on " + endpoint + ": " + str(e))
            if attempt < 2:
                time.sleep(3)
            else:
                return {}


def discover_network(network_id):
    print("Fetching network " + str(network_id))
    shows = []
    for page in range(1, 4):
        data = tmdb_get("/discover/tv", {
            "page": page,
            "include_adult": "false",
            "include_null_first_air_dates": "false",
            "sort_by": "popularity.desc",
            "with_networks": network_id,
            "first_air_date.gte": CUTOFF,
            "first_air_date.lte": TODAY_STR,
            "vote_count.gte": 20,
            "vote_average.gte": 6,
        })
        results = data.get("results", [])
        shows.extend(results)
        if len(results) < 20:
            break
    print("Found " + str(len(shows)) + " shows")
    return shows


def calculate_score(show):
    first_air = show.get("first_air_date")
    if first_air:
        try:
            age = (TODAY - datetime.date.fromisoformat(first_air)).days
        except Exception:
            age = 999
    else:
        age = 999

    popularity = show.get("popularity", 0)
    votes = show.get("vote_count", 0)
    rating = show.get("vote_average", 0)

    return popularity * 2 + votes * 0.4 + rating * 10 - age * 0.5


def clean_results(all_shows):
    cleaned = {}
    for show, network_name in all_shows:
        show_id = show.get("id")
        if not show_id:
            continue
        if show_id not in cleaned:
            show["matched_network"] = network_name
            cleaned[show_id] = show

    final = list(cleaned.values())
    for show in final:
        show["score"] = calculate_score(show)

    final.sort(key=lambda x: x["score"], reverse=True)
    return final


def select_top_shows(shows):
    selected = []
    service_limits = {
        "Netflix": 2,
        "Disney+": 1,
        "Apple TV+": 1,
        "Prime Video": 1,
        "MGM+": 1,
        "Sky Max": 1,
    }
    service_counts = {key: 0 for key in service_limits}

    for show in shows:
        service = show.get("matched_network")
        if service in service_limits:
            if service_counts[service] < service_limits[service]:
                selected.append(show)
                service_counts[service] += 1
        if
