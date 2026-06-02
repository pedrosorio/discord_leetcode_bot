from dataclasses import dataclass, fields
import json
import logging
import os
import requests
import time
from typing import List

log = logging.getLogger(__name__)

ENTRANTHUB_BASE     = "https://api.entranthub.com"
ENTRANTHUB_CONTESTS = ENTRANTHUB_BASE + "/api/v1/contests/leetcode/contests"
ENTRANTHUB_RANKINGS = ENTRANTHUB_BASE + "/api/v1/contests/leetcode/contests/{contest}/rankings"
LEETCODE_GRAPHQL    = "https://leetcode.com/graphql"
RANKINGS_CACHE_DIR  = "rankings_cache"

ENTRANTHUB_HEADERS = {
    "Origin": "https://entranthub.com",
    "Referer": "https://entranthub.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def get_last_contest_names(num=1):
    response = requests.get(
        ENTRANTHUB_CONTESTS,
        params={"status": "past", "limit": num, "offset": 0},
        headers=ENTRANTHUB_HEADERS,
    )
    log.info("%s", response.status_code)
    data = response.json()
    contests = data["items"]
    # predictedAt is null until EntrantHub finishes computing predictions (~1h after contest end).
    # Raise so the outer retry loop in posting_job.py keeps waiting.
    if not contests or contests[0].get("predictedAt") is None:
        raise ValueError("predictions not available yet for the most recent contest")
    names = [contest["titleSlug"] for contest in contests]
    log.info("latest contest(s): %s", names)
    return names


@dataclass
class RatingPrediction:
    new_rating: float
    delta_rating: float

RATING_PREDICTION_FIELDS = set([f.name for f in fields(RatingPrediction)])

@dataclass
class FullUserPrediction(RatingPrediction):
    username: str
    rank: int
    country_code: str

FULL_USER_PREDICTION_FIELDS = set([f.name for f in fields(FullUserPrediction)])

@dataclass
class DiscordUserPrediction(FullUserPrediction):
    discord_user_id: int


def fetch_country_code(username: str) -> str | None:
    query = '{ matchedUser(username: "%s") { profile { countryCode } } }' % username
    try:
        res = requests.post(LEETCODE_GRAPHQL, json={"query": query}, timeout=5)
        matched = res.json()["data"]["matchedUser"]
        if matched:
            code = matched["profile"]["countryCode"]
            log.info("country_code for %s: %s", username, code)
            return code
    except Exception as ex:
        log.info("fetch_country_code failed for %s: %s", username, ex)
    log.info("country_code for %s: None", username)
    return None


def _get_rankings(contest_name: str) -> list:
    """
    Returns the full rankings list for a contest.
    Uses a JSONL cache file (one entry per line, sentinel {"__complete__": true} at end).
    On first call fetches from the API and writes to cache incrementally — each page is
    flushed to disk before the next request, so a mid-fetch failure can be resumed from
    the correct offset on the next run rather than restarting from scratch.
    """
    os.makedirs(RANKINGS_CACHE_DIR, exist_ok=True)
    path = os.path.join(RANKINGS_CACHE_DIR, f"{contest_name}.jsonl")
    items = []
    complete = False

    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if "__complete__" in obj:
                    complete = True
                else:
                    items.append(obj)
        log.info("cache: %d entries (%s)", len(items), "complete" if complete else f"partial, resuming from offset {len(items)}")

    if complete:
        return items

    url = ENTRANTHUB_RANKINGS.format(contest=contest_name)
    offset = len(items)
    limit = 100

    with open(path, "a") as f:
        while True:
            res = requests.get(
                url,
                params={"limit": limit, "offset": offset},
                headers=ENTRANTHUB_HEADERS,
                timeout=10,
            )
            log.info("%s", res.status_code)
            res.raise_for_status()
            data = res.json()
            page_items = data.get("items", [])
            total = data.get("total", 0)

            for item in page_items:
                f.write(json.dumps(item) + "\n")
            f.flush()
            items.extend(page_items)
            log.info("rankings offset=%d total=%d fetched_so_far=%d", offset, total, len(items))

            offset += limit
            if not page_items or offset >= total:
                f.write(json.dumps({"__complete__": True}) + "\n")
                log.info("fetch complete, %d total entries cached", len(items))
                break
            time.sleep(0.5)

    return items


def fetch_users_for_contest(contest_name: str, usernames: set) -> dict:
    """
    Returns a dict mapping each username to a FullUserPrediction.
    Full rankings are loaded via _get_rankings (cached JSONL, resumable on failure).
    Matching is case-insensitive since the API returns lowercase slugs regardless of
    the original LeetCode username casing.
    Users not found in the rankings (did not participate) get a prediction with all
    numeric fields set to None.
    """
    all_items = _get_rankings(contest_name)

    # Case-insensitive lookup: lowercase registered username -> original casing
    lower_to_original = {u.lower(): u for u in usernames}
    found = {}  # original username -> ranking item

    for item in all_items:
        slug_lower = item["userSlug"].lower()
        if slug_lower in lower_to_original:
            original = lower_to_original[slug_lower]
            if original not in found:
                found[original] = item
                log.info("found %s at rank %d (newRating=%s, deltaRating=%s)", original, item["rank"], item["newRating"], item["deltaRating"])

    log.info("matched %d/%d registered users in rankings", len(found), len(usernames))
    not_found = set(usernames) - set(found)
    if not_found:
        log.info("did not participate: %s", not_found)

    results = {}
    for username in usernames:
        if username in found:
            item = found[username]
            country_code = fetch_country_code(username)
            results[username] = FullUserPrediction(
                username=username,
                rank=item["rank"],
                country_code=country_code,
                new_rating=item["newRating"],
                delta_rating=item["deltaRating"],
            )
        else:
            results[username] = FullUserPrediction(
                **{k: (username if k == "username" else None) for k in FULL_USER_PREDICTION_FIELDS}
            )
    return results


def get_top_users(contest_name, num_users=20, skip=0):
    url = ENTRANTHUB_RANKINGS.format(contest=contest_name)
    res = requests.get(
        url,
        params={"limit": num_users, "offset": skip},
        headers=ENTRANTHUB_HEADERS,
        timeout=10,
    )
    log.info("%s", res.status_code)
    data = res.json()
    return [
        FullUserPrediction(
            username=row["userSlug"],
            rank=row["rank"],
            country_code=None,
            new_rating=row["newRating"],
            delta_rating=row["deltaRating"],
        )
        for row in data.get("items", [])
    ]


def get_flag(country_code):
    return ''.join([chr(ord(c.upper()) + ord('🇦') - ord('A')) for c in country_code])

def format_message_for_users(contest: str, predictions: List[DiscordUserPrediction]) -> str:
    max_rank_len = max([len(str(up.rank)) for up in predictions])
    max_username_len = max([len(up.username) for up in predictions] + [len('Average')])
    max_new_rating_len = max([len(f'{up.new_rating:+.2f}') for up in predictions])
    max_delta_rating_len = max([len(f'{up.delta_rating:+.2f}') for up in predictions])

    msg = [f'Predictions for {contest}']
    rows = []
    mentions = []
    for up in sorted(predictions, key=lambda up: up.rank):
        mentions.append(f'<@{up.discord_user_id}>')
        row = '   '.join([
            f'`#{up.rank:<{max_rank_len}}`',
            f'`{up.username:<{max_username_len}}`',
            get_flag(up.country_code if up.country_code else 'AQ'),
            f'`{up.delta_rating:=+{max_delta_rating_len}.2f}`',
            f'`={up.new_rating:{max_new_rating_len}.2f}`'
            ])
        rows.append(row)

    average_delta = sum([up.delta_rating for up in predictions]) / len(predictions)
    average_rating = sum([up.new_rating for up in predictions]) / len(predictions)
    rows.append('   '.join([
        f'` {max_rank_len * " "}`',
        f'`{"Average":<{max_username_len}}`',
        get_flag('AQ'),
        f'`{average_delta:+{max_delta_rating_len}.2f}`',
        f'`={average_rating:{max_new_rating_len}.2f}`'
    ]))
    msgs = []
    for i in range((len(rows)-1)//10 + 1):
        msg = [f'Predictions for {contest}'] if i == 0 else []
        msg += rows[10*i:10*(i+1)]
        msgs.append('\n'.join(msg))
    msgs.append(' '.join(mentions))
    return msgs
