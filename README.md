# r/synthesizers Controversial bot

This bot scans new posts and determines their controversiality level. If the configured controversiality threshold is reached, the bot will leave a distinguished comment at the top of the thread warning users to play nice.

Controversiality is determined via the ratio of negative to postive comments, as determined by:

    1. User reports on the comment
    1. Downvotes on the comment
    3. Sentiment of the comment
    4. Reddit's controversiality flag on the comment

By default, the bot will monitor the (up to) 25 newest submissions to the subreddit, waiting until the submission is at least 60 minutes old and has at least 10 top-level comments before actioning. The default threshold for negative to postive comments is 33%, which represents about 2.5% of r/synthesizers posts with over 10 top-level comments.

# Installation

1. `pip install --user -r requirements.txt`
2. You'll need to create a personal use script on [Reddit's app portal](https://ssl.reddit.com/prefs/apps/). The developer should be a mod on the subreddit that the bot will monitor.
3. Modify praw.ini with your client id and client secret (from Reddit's app portal) along with the developer's Reddit username and password.
4. The script is stateless and does its work in one pass. It's intended to run periodically via cron or AWS Lambda, etc.
