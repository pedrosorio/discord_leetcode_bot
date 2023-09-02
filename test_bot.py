from discord_utils import *
from prediction_utils import *

discord_to_leetcode_map = {
        'tolga': 'tpoyraz22',
        'pedrosorio': 'pedro',
        'Nick': 'nskybytskyi',
        'Qiqi Impact': 'twitch_tv_qiqi_impact',
        'Flame': 'Sandeep_P',
        'betsymp': 'betsymp'
        }

print(get_user(663105721742917647))

post_message('Test message from the bot')

# last_contest = get_last_contest_names()[0]
last_contest = 'weekly-contest-359'
print(last_contest)


# print(get_top_users('biweekly-contest-111', num_users=10, skip=4150))
# print(get_top_users(last_contest))



print(get_flag('PT'))


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

# post_message(msg)

