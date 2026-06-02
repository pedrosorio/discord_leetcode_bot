# Migration Plan: lccn.lbao.site → EntrantHub API

## Problem

The third-party prediction API at `lccn.lbao.site` is dead. The domain was acquired by
**EntrantHub** (`entranthub.com`), a hackathon/contest aggregator that now happens to also
serve LeetCode contest rankings and rating predictions. All requests to `lccn.lbao.site`
return an HTTP 200 with the EntrantHub homepage HTML, causing `json.loads()` to raise
`"Expecting value: line 1 column 1 (char 0)"` on every attempt.

The weekly posting job has been failing since ~May 31 2026, looping 240 times (2 hours)
before giving up.

---

## Old API (dead)

Base: `https://lccn.lbao.site/api/v1`

| Purpose | Endpoint |
|---|---|
| List contests | `GET /contests/?skip={skip}&limit={limit}` |
| Per-user lookup | `GET /contest-records/user?contest_name={contest}&username={username}&archived=false` |
| Bulk predictions | `POST /contest-records/predicted-rating` |

Response for contest list was a **flat JSON array**:
```json
[{ "titleSlug": "weekly-contest-503", ... }, ...]
```

Response for per-user lookup was a **flat JSON array** (0 or 1 element):
```json
[{ "username": "pedro", "rank": 42, "country_code": "PT", "new_rating": 1700.0, "delta_rating": +25.0 }]
```

---

## New API: EntrantHub

### Access

- Base URL: `https://api.entranthub.com`
- All routes are behind Cloudflare bot protection.
- **The API passes through when requests include `Origin: https://entranthub.com`** (plus a
  realistic `User-Agent`). Without this header, Cloudflare returns an HTML challenge page.

Required headers for all requests:
```python
ENTRANTHUB_HEADERS = {
    "Origin": "https://entranthub.com",
    "Referer": "https://entranthub.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}
```

### Endpoints

#### Contest list

```
GET /api/v1/contests/leetcode/contests?status=past&limit={limit}&offset={offset}
```

Response (paginated wrapper — **not** a flat list):
```json
{
  "items": [
    {
      "titleSlug": "weekly-contest-504",
      "startTime": "2026-05-31T02:30:00Z",
      "predictedAt": "2026-05-31T04:55:55.290150Z",
      "userNumTotal": 34267,
      ...
    }
  ],
  "total": 605,
  "limit": 1,
  "offset": 0
}
```

Items are sorted **most-recent-first**. `items[0].titleSlug` is the latest past contest.
Prediction data is available roughly 2.5 hours after contest start (once `predictedAt` is set).

#### Rankings for a contest

```
GET /api/v1/contests/leetcode/contests/{titleSlug}/rankings?limit={limit}&offset={offset}
```

- Max `limit` is **100**.
- Results are sorted **by rank ascending** (rank 1 first).
- Predictions (`newRating`, `deltaRating`) are present as soon as the contest is processed.

Response (paginated):
```json
{
  "items": [
    {
      "dataRegion": "US",
      "userSlug": "pedro",
      "rank": 42,
      "score": 19,
      "finishTime": "2026-05-31T02:34:52Z",
      "oldRating": 1675.0,
      "newRating": 1700.0,
      "deltaRating": 25.0,
      "attendedContestsCount": 15,
      "avatarUrl": "..."
    }
  ],
  "total": 34267,
  "limit": 100,
  "offset": 0
}
```

**No per-user lookup endpoint exists.** To find a specific user, you must paginate through
rankings and scan for their `userSlug`.

### Field mapping: old → new

| Old field | New field | Notes |
|---|---|---|
| `username` | `userSlug` | same value |
| `rank` | `rank` | unchanged |
| `new_rating` | `newRating` | camelCase |
| `delta_rating` | `deltaRating` | camelCase |
| `country_code` | *(absent)* | must fetch separately — see below |

---

## Country Code: LeetCode GraphQL

LeetCode exposes a public GraphQL API that returns `countryCode` (ISO 3166-1 alpha-2) for
any user. No authentication required, no Cloudflare protection.

```
POST https://leetcode.com/graphql
Content-Type: application/json

{ "query": "{ matchedUser(username: \"pedro\") { profile { countryCode countryName } } }" }
```

Response:
```json
{ "data": { "matchedUser": { "profile": { "countryCode": "PT", "countryName": "Portugal" } } } }
```

Returns `null` for `matchedUser` if the user doesn't exist, and `null` for `countryCode` if
the user hasn't set a location. Both cases should fall back to `None`.

---

## Implementation Plan

All changes are in `/Users/pedrosorio/code/discord_leetcode_bot/prediction_utils.py`.
`posting_job.py` needs **no changes**.

### 1. Replace URL constants and add headers

Remove the four `LEETCODE_*` constants. Replace with:

```python
ENTRANTHUB_BASE    = "https://api.entranthub.com"
ENTRANTHUB_CONTESTS = ENTRANTHUB_BASE + "/api/v1/contests/leetcode/contests"
ENTRANTHUB_RANKINGS = ENTRANTHUB_BASE + "/api/v1/contests/leetcode/contests/{contest}/rankings"
LEETCODE_GRAPHQL    = "https://leetcode.com/graphql"

ENTRANTHUB_HEADERS = {
    "Origin": "https://entranthub.com",
    "Referer": "https://entranthub.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}
```

### 2. Update `get_last_contest_names(num=1)`

Old: `requests.get(url)` → flat list response  
New: paginated response — extract `data["items"]`

```python
def get_last_contest_names(num=1):
    response = requests.get(
        ENTRANTHUB_CONTESTS,
        params={"status": "past", "limit": num, "offset": 0},
        headers=ENTRANTHUB_HEADERS,
    )
    print(response.status_code)
    data = response.json()
    return [contest["titleSlug"] for contest in data["items"]]
```

### 3. Add `fetch_country_code(username)`

New helper that fetches ISO country code from LeetCode's GraphQL API. Called once per user.
Returns `None` if the user has no location set or the query fails.

```python
def fetch_country_code(username: str) -> str | None:
    query = '{ matchedUser(username: "%s") { profile { countryCode } } }' % username
    try:
        res = requests.post(LEETCODE_GRAPHQL, json={"query": query}, timeout=5)
        matched = res.json()["data"]["matchedUser"]
        if matched:
            return matched["profile"]["countryCode"]
    except Exception:
        pass
    return None
```

### 4. Replace `fetch_user_prediction()` with a batch-scan approach

The core problem: no per-user lookup endpoint exists. Calling `fetch_user_prediction` once
per user would require a full ranking scan each time (up to 34k entries / 100 per page = 343
pages), repeated N times for N users. This is wasteful.

**Better approach**: do **one paginated scan** per contest run that collects ALL registered
users in a single pass. Stop scanning early once every user is found.

Replace `fetch_user_prediction` with:

```python
def fetch_users_for_contest(
    contest_name: str, usernames: set[str]
) -> dict[str, FullUserPrediction]:
    """
    Scans contest rankings page-by-page and returns a FullUserPrediction for each
    username found. Users not found in the rankings did not participate.
    """
    url = ENTRANTHUB_RANKINGS.format(contest=contest_name)
    remaining = set(usernames)
    found: dict[str, dict] = {}
    offset = 0
    limit = 100

    while remaining:
        res = requests.get(
            url,
            params={"limit": limit, "offset": offset},
            headers=ENTRANTHUB_HEADERS,
            timeout=10,
        )
        data = res.json()
        items = data.get("items", [])
        total = data.get("total", 0)

        for item in items:
            slug = item["userSlug"]
            if slug in remaining:
                found[slug] = item
                remaining.discard(slug)

        offset += limit
        if not items or offset >= total:
            break

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
```

### 5. Update `posting_job.py`-compatible entry point

`posting_job.py` calls `fetch_missing_users_for_contest`, which in turn calls
`pu.fetch_user_prediction(contest_name, user)` in a loop.

Two options:
- **Option A** (minimal change): keep `fetch_user_prediction` as a wrapper that calls the
  batch function with a single-item set and returns one result. Simple but wastes the
  efficiency gain for multiple users.
- **Option B** (preferred): update `fetch_missing_users_for_contest` in `posting_job.py` to
  use the new batch function directly. Fetches all users in one scan.

Recommendation: **Option B**, since `fetch_missing_users_for_contest` already knows the full
`set_to_fetch` at call time.

### 6. Keep / update remaining functions

- **`get_top_users()`**: update to use the new rankings endpoint with paginated response shape.
  Not called by `posting_job.py` but may be used elsewhere.
- **`fetch_multiple_rating_predictions()`**: not called by `posting_job.py`; the old endpoint
  is dead. Can be removed or stubbed.
- **`get_flag()`, `format_message_for_users()`**: no changes needed.

---

## What doesn't change

- `posting_job.py` — no changes needed (with Option A above; minor change with Option B)
- `query_utils.py`, `discord_utils.py` — no changes
- The retry loop in `posting_job.py` (240 tries × 30s) still makes sense: if the contest
  just ended, predictions may not be in the rankings yet (check `predictedAt` field on the
  contest object)

---

## Risk / caveats

- **Cloudflare**: the `Origin` header bypass works today but is not guaranteed to work
  forever. If Cloudflare tightens restrictions, the bot will break again. A longer-term fix
  would be to contact the EntrantHub maintainer and request a public API key or allowlist the
  server's IP.
- **Scan depth**: if a registered user has a very low rank (e.g., rank 20,000+ in a 34k-user
  contest), the scan will take up to 200+ pages. For the typical small number of registered
  users this is acceptable, but worth monitoring.
- **Country code latency**: one GraphQL call per user per contest run. Small number of users
  means negligible cost. Could be cached in the DB if latency becomes an issue.
- **CN users**: the new API has `dataRegion: "US" | "CN"`. The old bot only ever used
  `data_region: "US"`. If any registered user is a CN-region account, their `userSlug` may
  appear under `dataRegion: "CN"` in rankings. For now, scanning all rankings (regardless of
  region) means we'll find them either way.
