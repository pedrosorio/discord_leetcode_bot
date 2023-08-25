from dataclasses import dataclass, fields
import json
import requests

DISCORD_API_URL = 'https://discord.com/api/channels/{channel_id}/messages' 
TEST_CHANNEL_ID = 1143698636929245254

TOKEN = open('TOKEN.txt').readlines()[0].strip()
print(TOKEN)
print(f'Bot {TOKEN}')

discord_to_leetcode_map = {
        'tolga': 'tpoyraz22',
        'pedrosorio': 'pedro',
        'Nick': 'nskybytskyi',
        'Qiqi Impact': 'twitch_tv_qiqi_impact',
        'Flame': 'Sandeep_P',
        'betsymp': 'betsymp'
        }

def post_message(message):
    response = requests.post(url=DISCORD_API_URL.format(channel_id=TEST_CHANNEL_ID), headers={'Authorization': f'Bot {TOKEN}'}, json={'content': message})
    print(response.status_code)
    print(response.content)

#post_message('Test message from the bot')

LEETCODE_PREDICT_URL = "https://lccn.lbao.site/api/v1"
LEETCODE_CONTESTS = LEETCODE_PREDICT_URL +  "/contests/?skip={skip}&limit={limit}"
LEETCODE_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/?contest_name={contest}&archived=false&skip={skip}&limit={limit}"
LEETCODE_USER_PREDICTIONS = LEETCODE_PREDICT_URL + "/contest-records/user?contest_name={contest}&username={username}&archived=false"

def get_last_contest_name():
    response = requests.get(LEETCODE_CONTESTS.format(skip=0, limit=1))
    print(response.status_code)
    print(response.content)
    return json.loads(response.content.decode('utf-8'))[0]['titleSlug']

# last_contest = get_last_contest_name()
last_contest = 'weekly-contest-359'
print(last_contest)


def get_top_users(contest_name, num_users=20, skip=0):
    url = LEETCODE_PREDICTIONS.format(contest=contest_name, skip=skip, limit=num_users)
    print(url)
    response = requests.get(url)
    print(response.status_code)
    return response.content

# print(get_top_users('biweekly-contest-111', num_users=10, skip=4150))
# print(get_top_users(last_contest))


@dataclass
class UserPrediction:
    username: str
    rank: int
    new_rating: float
    delta_rating: float
    country_code: str

USER_PREDICTION_FIELDS = set([f.name for f in fields(UserPrediction)])

def get_user_prediction(contest_name, username):
    url = LEETCODE_USER_PREDICTIONS.format(contest=contest_name, username=username)
    data = requests.get(url).content
    print(data)
    json_data = json.loads(data.decode('utf-8'))[0]
    print(json_data)
    return UserPrediction(**{k: json_data[k] for k in json_data if k in USER_PREDICTION_FIELDS})


def get_flag(country_code):
    return ''.join([chr(ord(c.upper()) + ord('🇦') - ord('A')) for c in country_code])

print(get_flag('PT'))


def format_message_for_users(contest, users_predictions):
    max_rank_len = max([len(str(up.rank)) for up in users_predictions])
    max_username_len = max([len(up.username) for up in users_predictions])
    max_new_rating_len = max([len(f'{up.new_rating:+.2f}') for up in users_predictions])
    max_delta_rating_len = max([len(f'{up.delta_rating:+.2f}') for up in users_predictions])
    msg = []
    for up in sorted(users_predictions, key=lambda up: up.rank):
        row = '   ' .join([
            f'`#{up.rank:<{max_rank_len}}`',
            f'`{up.username:<{max_username_len}}`',
            get_flag(up.country_code) if up.country_code else '`  `',
            f'`{up.delta_rating:=+{max_delta_rating_len}.2f}`',
            f'`={up.new_rating:{max_new_rating_len}.2f}`'
            ])
        msg.append(row)
    return '\n'.join(msg)


# print(get_user_prediction('biweekly-contest-111', 'Sandeep_P'))

#up = get_user_prediction(last_contest, 'pedro')
#print(up)
up = UserPrediction(username='pedro', rank=469, new_rating=2631.3975353504316, delta_rating=-10.425104966194748, country_code='PT')
up2 = UserPrediction(username='betsymp', rank=152, new_rating=2544.44341232, delta_rating=30.25, country_code='CN')
up3 = UserPrediction(username='nskybytskyi', rank=20, new_rating=2919.0512315, delta_rating=103.13, country_code='UA')
up4 = UserPrediction(username='Sandeep_P', rank=4152, new_rating=2075.235713266213, delta_rating=-22.56223180104167, country_code='IN')

msg = format_message_for_users(last_contest, [up, up2, up3, up4])
print(len(msg))
print(msg)

post_message(msg)

