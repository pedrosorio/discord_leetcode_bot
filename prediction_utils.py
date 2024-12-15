from dataclasses import dataclass, fields
import json
import requests
from typing import List
import time

LEETCODE_PREDICT_URL = "https://lccn.lbao.site/api/v1"
LEETCODE_CONTESTS = LEETCODE_PREDICT_URL +  "/contests/?skip={skip}&limit={limit}"
LEETCODE_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/?contest_name={contest}&archived=false&skip={skip}&limit={limit}"
LEETCODE_USER_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/user?contest_name={contest}&username={username}&archived=false"
LEETCODE_MULTIPLE_USER_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/predicted-rating"


def get_last_contest_names(num=1):
    response = requests.get(LEETCODE_CONTESTS.format(skip=0, limit=num))
    print(response.status_code)
    print(response.content)
    return [contest['titleSlug'] for contest in json.loads(response.content.decode('utf-8'))]

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


def get_top_users(contest_name, num_users=20, skip=0):
    url = LEETCODE_PREDICTIONS.format(contest=contest_name, skip=skip, limit=num_users)
    response = requests.get(url)
    print(response.status_code)
    json_data = json.loads(response.content.decode('utf-8'))
    return [FullUserPrediction(**{k: row[k] for k in row if k in FULL_USER_PREDICTION_FIELDS}) for row in json_data]


def fetch_user_prediction(contest_name, username) -> FullUserPrediction:
    url = LEETCODE_USER_PREDICTIONS.format(contest=contest_name, username=username)
    tries = 0
    while True:
        if tries > 0:
            time.sleep(1)
        tries += 1
        try:
            res = requests.get(url, timeout=5)
            print(res.status_code)
            if res.status_code == 200:
                break
        except Exception as ex:
            print("exception", ex)
    print(f"successful after {tries} requests")
    data = res.content
    print(data)
    json_data = json.loads(data.decode('utf-8'))
    if not json_data:
        return FullUserPrediction(**{k: (username if k == 'username' else None) for k in FULL_USER_PREDICTION_FIELDS})
    json_data = json_data[0]
    print(json_data)
    return FullUserPrediction(**{k: json_data[k] for k in json_data if k in FULL_USER_PREDICTION_FIELDS})

def fetch_multiple_rating_predictions(contest_name: str, users: List[str]) -> List[RatingPrediction]:
    url = LEETCODE_MULTIPLE_USER_PREDICTIONS
    response = requests.post(url, json = {'contest_name': contest_name, 'users': [{'username': user, 'data_region': 'US'} for user in users]})
    json_data = json.loads(response.content.decode('utf-8'))
    print(json_data)
    return [RatingPrediction(**{k: json_row[k] for k in json_row if k in RATING_PREDICTION_FIELDS}) if json_row is not None else None for json_row in json_data] 


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
        row = '   ' .join([
            f'`#{up.rank:<{max_rank_len}}`',
            f'`{up.username:<{max_username_len}}`',
            get_flag(up.country_code if up.country_code else 'AQ'),
            f'`{up.delta_rating:=+{max_delta_rating_len}.2f}`',
            f'`={up.new_rating:{max_new_rating_len}.2f}`'
            ])
        rows.append(row)

    average_delta = sum([up.delta_rating for up in predictions]) / len(predictions)
    average_rating = sum([up.new_rating for up in predictions]) / len(predictions)
    rows.append('   ' .join([
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
