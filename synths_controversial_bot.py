import datetime
import json
import os

import praw

DEFAULT_SUBREDDIT_NAME = 'synthesizers'

SENTIMENT_THRESHHOLD = 0.5
WARN_THRESHOLD = 0.7
MAX_SUBMISSIONS_TO_PROCESS = 50
MIN_COMMENTS_TO_WARN = 10
MIN_SUBMISSION_AGE_TO_PROCESS = 60


class SynthsControversialBot:
    def __init__(self, subreddit_name=DEFAULT_SUBREDDIT_NAME, dry_run=False):
        self.dry_run = dry_run

        self.reddit = praw.Reddit('SynthsControversialBot')
        self.subreddit = self.reddit.subreddit(subreddit_name)

        self.warning = self.read_text_file('controversial-warning.txt')
        self.weights = self.read_json_file('controversial-weights.json')

    def scan(self):
        for submission in self.subreddit.new(limit=MAX_SUBMISSIONS_TO_PROCESS):
            if (self.is_actionable(submission)
                    and self.calc_submission_age(submission) >= MIN_SUBMISSION_AGE_TO_PROCESS
                    and submission.num_comments >= MIN_COMMENTS_TO_WARN):
                self.process_submission(submission)

    def process_submission(self, submission):
        sentiment = self.calc_comments_sentiment(submission)

        print(f'{submission.title}: {sentiment:.2f}')

        if sentiment <= SENTIMENT_THRESHHOLD and not self.was_warned(submission):
            self.warn(submission, sentiment)
        elif sentiment <= WARN_THRESHOLD:
            self.log('Trending', submission, sentiment)

    # return a number between -1.0 and 1.0 where -1.0 is the most negative and 1.0 is the most positive
    def calc_comments_sentiment(self, submission):
        sentiment = 1.0

        comments = submission.comments
        comments.replace_more(limit=None)
        comments_list = comments.list()

        num_comments = len(comments_list)
        negative_signals = 0

        for comment in comments_list:
            if comment.score <= 0:
                negative_signals += 1

            if comment.removed:
                negative_signals += 1

            negative_signals += comment.controversiality
            negative_signals += self.calc_user_reports_count(comment)

        if num_comments > 0:
            sentiment = -1.0 + 2.0 / (1.0 + negative_signals / num_comments)

        return sentiment

    def warn(self, submission, sentiment):
        if not self.dry_run:
            bot_comment = submission.reply(self.warning)
            bot_comment.mod.distinguish(sticky=True)
            bot_comment.mod.ignore_reports()

            submission.report('Heads up. This thread is trending controversial.')

        self.log('Warned', submission, sentiment)

    def was_warned(self, submission):
        warned = False

        if len(submission.comments) > 0:
            first_comment = submission.comments[0]
            warned = (first_comment.distinguished == 'moderator'  # don't collide with other mods or mod bots
                      or first_comment.author.name == self.reddit.config.username)

        return warned

    @ staticmethod
    def is_actionable(submission):
        return (not submission.distinguished == 'moderator'
                and not submission.approved
                and not submission.removed
                and not submission.locked)

    @ staticmethod
    def calc_user_reports_count(obj):
        count = len(obj.user_reports)

        if hasattr(obj, 'user_reports_dismissed'):
            count += len(obj.user_reports_dismissed)

        return count

    @ staticmethod
    def calc_submission_age(submission):
        now = datetime.datetime.now()
        created = datetime.datetime.fromtimestamp(submission.created_utc)
        age = now - created

        return age.total_seconds() / 60

    @ staticmethod
    def read_text_file(filename):
        with open(filename, encoding='utf-8') as file:
            text = file.read()

        return text

    @ staticmethod
    def read_json_file(filename):
        with open(filename, encoding='utf-8') as file:
            data = json.load(file)

        return data

    def log(self, message, submission, sentiment):
        is_dry_run = '*' if self.dry_run is True else ''
        name = type(self).__name__
        now = datetime.datetime.now()
        print(f'{is_dry_run}[{name}][{now}] {message}: "{submission.title}" ({sentiment:.2f}) ({submission.id})')


def lambda_handler(event=None, context=None):
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    bot = SynthsControversialBot(subreddit_name=subreddit_name, dry_run=dry_run)
    bot.scan()


if __name__ == '__main__':
    lambda_handler()
