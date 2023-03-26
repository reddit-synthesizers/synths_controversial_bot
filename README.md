# r/synthesizers Controversial bot

This bot scans new posts and determines their controversiality level by negative activity in the comments. If the configured threshold of negative to positive comments is reached, the bot will leave a distinguished comment at the top of the thread warning users to play nice.

A comment is considered negative by:

    1. User reports on the comment
    2. Downvotes on the comment
    3. Sentiment of the comment [1]
    4. Reddit's controversiality flag for the comment

By default, the bot will monitor the (up to) 50 newest submissions to the subreddit, waiting until the submission is at least 60 minutes old and has at least 10 top-level comments before actioning. The default threshold for negative to postive comments is 33%. In the case of r/synthesizers this threshold is breached in ~1% of posts containing 10 or more top-level comments. 

# Installation

1. `pip install --user -r requirements.txt`
2. You'll need to create a personal use script on [Reddit's app portal](https://ssl.reddit.com/prefs/apps/). The developer should be a mod on the subreddit that the bot will monitor.
3. Modify praw.ini with your client id and client secret (from Reddit's app portal) along with the developer's Reddit username and password.
4. The script is stateless and does its work in one pass. It's intended to run periodically via cron or AWS Lambda, etc.

# Notes

This bot was designed to run periodically, either via a cron job or in a serverless environment. Many of the design decisions going into it (e.g., statelessness) were driven by the desire to run it as a Lambda on the AWS free tier. For r/synthesizers, a medium sized sub (~300k subscribers), the bot runs in ~5 seconds on average. When run every 15 minutes this consumes ~3k requests and ~2k GB-seconds per month (3K * 5s * 0.128GB) which is a fraction of the 1MM requests, 400K GB-seconds per month AWS free tier limit. The bot uses an average of 4 Reddit API calls per invocation on the happy path (more when it has to go deep and pull in commment forests), putting it well under the Reddit API limit of 60 requests per minute. For larger subs, configured with a higher value for MAX_SUBMISSIONS_TO_PROCESS YMMV.

[1] See [vaderSentiment](https://github.com/vaderSentiment/vaderSentiment)