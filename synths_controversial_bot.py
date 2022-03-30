import praw
import datetime
import json
import math
import os

from praw.models import MoreComments

DEFAULT_SUBREDDIT_NAME = 'synthesizers'

MIN_COMMENTS_TO_WARN = 10
MIN_AGE_TO_WARN = 30
SCORE_THRESHHOLD = 20
MAX_SUBMISSIONS_TO_PROCESS = 50


class SynthsControversialBot:
    def __init__(self, subreddit_name=DEFAULT_SUBREDDIT_NAME, dry_run=False):
        self.dry_run = dry_run

        self.reddit = praw.Reddit('SynthRulesBot')
        subreddit = self.reddit.subreddit(subreddit_name)

        self.warning = self.read_text_file('controversial-warning.txt')
        self.keywords = self.read_keywords_file('controversial-keywords.json')

        # for submission in subreddit.search('title:behringer', sort='new', limit=100):
        for submission in subreddit.new(limit=MAX_SUBMISSIONS_TO_PROCESS):
            self.process_submission(submission)

    def process_submission(self, submission):
        score = self.get_title_weight(submission)
        age = self.get_submission_age(submission)
        downvoted_comments = 0

        if (score > 0
                and age >= MIN_AGE_TO_WARN
                and submission.num_comments >= MIN_COMMENTS_TO_WARN
                and not submission.approved
                and not submission.removed
                and not submission.locked):

            score += self.get_user_reports_count(submission)

            for comment in submission.comments.list():
                if isinstance(comment, MoreComments):  # ignoring MoreComments (for now)
                    continue

                if comment.removed:
                    score += 1

                score += comment.controversiality
                score += self.get_user_reports_count(comment)

                if comment.score <= 0:
                    downvoted_comments += 1

            score += math.ceil(downvoted_comments / submission.num_comments * 100)

            if score >= SCORE_THRESHHOLD:
                self.warn(submission, score)

    def get_title_weight(self, submission):
        weight = 0

        title = submission.title.lower()
        for word in self.keywords:
            if title.find(word) >= 0:
                weight = weight + self.keywords[word]

        return weight

    def get_user_reports_count(self, object):
        count = len(object.user_reports)

        if hasattr(object, 'user_reports_dismissed'):
            count += len(object.user_reports_dismissed)

        return count

    def warn(self, submission, score):
        if not self.was_warned(submission):
            if not self.dry_run:
                bot_comment = submission.reply(self.warning)
                bot_comment.mod.distinguish(sticky=True)
                bot_comment.mod.ignore_reports()

                submission.report('Heads up. This thread is trending controversial.')

            self.log('Warned (score=' + str(score) + ')', submission)

    def get_submission_age(self, submission):
        now = datetime.datetime.now()
        created = datetime.datetime.fromtimestamp(submission.created_utc)
        age = now - created

        return age.total_seconds() / 60

    def was_warned(self, submission):
        warned = False

        if len(submission.comments) > 0:
            first_comment = submission.comments[0]
            warned = (first_comment.distinguished == 'moderator'  # don't collide with other mods or mod bots
                      or first_comment.author.name == self.reddit.user.me())

        return warned

    def read_text_file(self, filename):
        text = {}

        file = open(filename, 'r')
        text = file.read()
        file.close()

        return text

    def read_keywords_file(self, filename):
        data = {}

        file = open(filename, 'r')
        data = json.load(file)
        file.close()

        return data

    def log(self, message, submission):
        now = datetime.datetime.now()
        name = type(self).__name__
        print(f'[{name}][{now}] {message}: \'{submission.title}\' ({submission.id})')


def lambda_handler(event=None, context=None):
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    SynthsControversialBot(subreddit_name=subreddit_name, dry_run=dry_run)


if __name__ == '__main__':
    lambda_handler()
