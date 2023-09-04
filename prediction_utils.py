from dataclasses import dataclass, fields
import json
import requests
from typing import List

LEETCODE_PREDICT_URL = "https://lccn.lbao.site/api/v1"
LEETCODE_CONTESTS = LEETCODE_PREDICT_URL +  "/contests/?skip={skip}&limit={limit}"
LEETCODE_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/?contest_name={contest}&archived=false&skip={skip}&limit={limit}"
LEETCODE_USER_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/user?contest_name={contest}&username={username}&archived=false"

def get_last_contest_names(num=1):
    response = requests.get(LEETCODE_CONTESTS.format(skip=0, limit=num))
    print(response.status_code)
    print(response.content)
    return [contest['titleSlug'] for contest in json.loads(response.content.decode('utf-8'))]

@dataclass
class UserPrediction:
    username: str
    rank: int
    new_rating: float
    delta_rating: float
    country_code: str

@dataclass
class DiscordUserPrediction(UserPrediction):
    discord_user_id: int

USER_PREDICTION_FIELDS = set([f.name for f in fields(UserPrediction)])

def get_top_users(contest_name, num_users=20, skip=0):
    url = LEETCODE_PREDICTIONS.format(contest=contest_name, skip=skip, limit=num_users)
    response = requests.get(url)
    print(response.status_code)
    json_data = json.loads(response.content.decode('utf-8'))
    return [UserPrediction(**{k: row[k] for k in row if k in USER_PREDICTION_FIELDS}) for row in json_data]


def fetch_user_prediction(contest_name, username) -> UserPrediction:
    url = LEETCODE_USER_PREDICTIONS.format(contest=contest_name, username=username)
    data = requests.get(url).content
    print(data)
    json_data = json.loads(data.decode('utf-8'))
    if not json_data:
        return UserPrediction(username, *(len(USER_PREDICTION_FIELDS)-1)*[None])
    json_data = json_data[0]
    print(json_data)
    return UserPrediction(**{k: json_data[k] for k in json_data if k in USER_PREDICTION_FIELDS})

def get_flag(country_code):
    return ''.join([chr(ord(c.upper()) + ord('🇦') - ord('A')) for c in country_code])

def format_message_for_users(contest: str, predictions: List[DiscordUserPrediction]) -> str:
    max_rank_len = max([len(str(up.rank)) for up in predictions])
    max_username_len = max([len(up.username) for up in predictions])
    max_new_rating_len = max([len(f'{up.new_rating:+.2f}') for up in predictions])
    max_delta_rating_len = max([len(f'{up.delta_rating:+.2f}') for up in predictions])
    msg = [f'Predictions for {contest}']
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
        msg.append(row)
    msg.append(' '.join(mentions))
    msg.append("If you would like to join, type /register_leetcode_user in any channel on this discord server to add yourself to the list")
    return '\n'.join(msg)