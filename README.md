# r/synthesizers Controversial bot

This bot scans new posts and determines their controversiality level. If the configured controversiality threshold is reached, the bot will leave a distinguished comment at the top of the thread warning users to play nice.

The bot determines controversiality via multiple signals:   

1. User reports on the submission
2. A low upvote ratio on the submission
3. The number of negative comments, as determined by:
    1. Downvotes on the comment
    2. Comment is deleted by the author or mod
    3. Reddit's controversiality rating of the comment
    4. User reports on the comment

By default, the bot will monitor the (up to) 50 newest submissions to the subreddit, waiting until the submission is at least 60 minutes old and has at least 10 top-level comments before actioning.

# Installation

1. `pip install --user -r requirements.txt`
2. You'll need to create a personal use script on [Reddit's app portal](https://ssl.reddit.com/prefs/apps/). The developer should be a mod on the subreddit that the bot will monitor.
3. Modify praw.ini with your client id and client secret (from Reddit's app portal) along with the developer's Reddit username and password.
4. The script is stateless and does its work in one pass. It's intended to run periodically via cron or AWS Lambda, etc.
