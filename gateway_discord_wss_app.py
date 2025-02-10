import discord
import json
import logging
from query_utils import QueryUtils

logging.basicConfig(filename='leetcode_discord_bot_gateway_wss.log', level=logging.INFO, format="%(asctime)s:%(message)s")

query_utils = QueryUtils()

# Enable required intents
intents = discord.Intents.default()
intents.dm_messages = True  # For receiving DM events
intents.message_content = True  # For reading message content (optional)

client = discord.Client(intents=intents)

def get_all_leetcode_usernames_for_discord_user(discord_user_id: int) -> set[str]:
    return query_utils.get_all_leetcode_usernames_for_discord_user(discord_user_id)

def get_leetcode_user_contest_performances_messages(leetcode_username: str) -> list[str]:
    performances = query_utils.get_all_contest_performances_for_leetcode_username(leetcode_username)
    logging.info(f"DM-Process {leetcode_username} has {len(performances)} contests registered")
    if not performances:
        return [f"No contest performances found for LeetCode user {leetcode_username}."]
    
    message = f"Contest performances for LeetCode user {leetcode_username}:\n"

    max_contest_name_len = max([len(performance['contest_name']) for performance in performances] + [len("Contest Name")])
    max_rank_len = max([len(str(performance['rank'])) for performance in performances] + [len("Rank")-1])
    max_new_rating_len = max([len(f"{performance['new_rating']:.2f}") for performance in performances] + [len("New Rating")-1])
    max_delta_rating_len = max([len(f"{performance['delta_rating']:=+.2f}") for performance in performances] + [len("Delta")])

    header = '   '.join([
        f"`{'Contest Name':<{max_contest_name_len}}`",
        f"`{'Rank':<{max_rank_len+1}}`",
        f"`{'Delta':<{max_delta_rating_len}}`",
        f"`{'New Rating':<{max_new_rating_len}}`"
    ])
    rows = []
    for performance in performances:
        if any(value is None for value in performance.values()):
            continue
        rows.append('   '.join([
            f"`{performance['contest_name']:<{max_contest_name_len}}`",
            f"`#{performance['rank']:>{max_rank_len}}`",
            f"`{performance['delta_rating']:=+{max_delta_rating_len}.2f}`",
            f"`={performance['new_rating']:{max_new_rating_len}.2f}`"
        ]))
    msgs = []
    for i in range((len(rows)-1)//10 + 1):
        msg = [message + header] if i == 0 else []
        msg += rows[10*i:10*(i+1)]
        msgs.append('\n'.join(msg))
    print(msgs)
    return msgs

    

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Check if it's a DM
    if isinstance(message.channel, discord.DMChannel):
        logging.info(f"DM-Process {message.author.id} ({message.author.display_name}): {message.content}")
        message_intro = f"Hello {message.author.display_name}! I do not read user messages, but here is what I know about you:\n"
        leetcode_username_set = get_all_leetcode_usernames_for_discord_user(message.author.id)
        logging.info(f"DM-Process {message.author.display_name} leetcode names: {leetcode_username_set}")
        if leetcode_username_set:
            message_intro += f"Here are all the leetcode usernames you have registered: {', '.join(leetcode_username_set)}\n"
            await message.channel.send(message_intro)
            for leetcode_username in leetcode_username_set:
                contest_performances_messages = get_leetcode_user_contest_performances_messages(leetcode_username)
                for msg in contest_performances_messages:
                    await message.channel.send(msg)
        else:
            await message.channel.send("You have not registered any LeetCode usernames with this bot.")

# Run the bot
TOKEN = json.loads(open('SECRETS.txt').read())['TOKEN']
client.run(TOKEN)
