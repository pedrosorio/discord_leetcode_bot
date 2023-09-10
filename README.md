### Discord Bot for leetcode contest rating predictions


Discord bot that posts contest summary and rating change predictions after every leetcode contest for users in a discord server. Uses flask/gunicorn and sqlite for storage.

Predictions for weekly-contest-xxx

`#33  `   `WeekendCoder `   🇺🇸   `+111.25`   `= 2541.35`

`#83  `   `Top100Enjoyer`   🇺🇸   `+  9.25`   `= 2897.21`

`#150 `   `pedro        `   🇵🇹   `+ 20.00`   `= 2690.69`

`#3316`   `Beginner     `   🇦🇶   `+ 13.24`   `= 1889.14`

`#5493`   `Interviewer  `   🇦🇶   `- 28.44`   `= 2041.32`

Important files:
- [register_app_commands.py](register_app_commands.py) registers with discord the list of commands the bot supports (and their UI)
- [flask_app/interactions.py](flask_app/interactions.py) contains the code to handle the commands issued by users in a discord channel. Supports basic discord bot HTTP API functionality. Does not depend on a "discord bot" library.
- [posting_job.py](posting_job.py) is a script that polls https://lccn.lbao.site ([Github project](https://github.com/baoliay2008/lccn_predictor/tree/main)) every 30s until a new contest is published. Once a new contest is available, it fetches the rank and rating prediction for every user who registered with the bot and stores them in the DB. It uses this information to iterate over the discord servers where the bot is installed and sends a message to the corresponding channel summarizing the results of the users in that server.


Bot setup:
- See [discord docs](https://discord.com/developers/docs/getting-started) on how to create an application/bot
- Create a SECRETS.txt file in the home directory of the project (do not commit this) containing a json with the following keys: APPLICATION_ID, PUBLIC_KEY (present in your discord application's general information tab), and TOKEN (generated in Bot's page - *DO NOT* publish this one)
- Create virtualenv, activate it and install requirements: `python3 -m venv venv; source venv/bin/activate; pip install -r requirements.txt`
- Register with discord the commands the bot can respond to: `python3 register_app_commands.py`
- Initialize the db: `flask init-db`
- Run the flask app through gunicorn: `gunicorn --bind 0.0.0.0:PORT wsgi:app`
- Fill in the interactions endpoint URL in the application's page so discord knows where to send requests from commands 

Bot installation in discord server:
- In the application page, OAuth2 -> Url Generator, the bot needs applications.commands and bot scope, and the bot needs "send messages" permissions.
- This will generate a url like this: https://discord.com/api/oauth2/authorize?client_id={your_application_id}&permissions=2048&scope=applications.commands%20bot
- Accessing the URL as a logged-in discord user prompts discord to ask for the discord server to install the bot in (you must havve "Manage Server" permissions). 
- [Enable developer mode in discord](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) and obtain the server id and channel id where you want the bot to post. Manually (yeah, I know) insert a row in the 'server_to_channel' table. TODO: make this possible via CLI, or even better, interaction with the bot in discord.