# r/synthesizers Controversial bot

This bot scans new posts and determines their controversial level. If the configured threshold is reached, the bot will leave a distinguished comment at the top of the thread warning users to play nice.

The bot determines controversiality on multiple factors:

1. Keywords[1] in the title.
2. Keywords in the body.
3. The number of user reports on the submission itself.
4. The number of user reports on individual comments.
5. The number of comments that Reddit flagged as controversial.
6. The ratio of negative to positive scored comments in the submission.

By default, the bot will monitor the (up to) 50 newest submissions to the subreddit, waiting until the submission is at least 60 minutes old and has at least 10 comments before actioning.

[1] Based on analysis of the frequency of non common words in recent controversial threads. See `controversial-keywords.json` for the words and individual weighting.

# Installation

1. `pip install --user -r requirements.txt`
2. You'll need to create a personal use script on [Reddit's app portal](https://ssl.reddit.com/prefs/apps/). The developer should be a mod on the subreddit that the bot will monitor.
3. Modify praw.ini with your client id and client secret (from Reddit's app portal) along with the developer's Reddit username and password.
4. The script is stateless and does its work in one pass. It's intended to run periodically via cron or AWS Lambda, etc.
