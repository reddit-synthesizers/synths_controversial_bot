import datetime
import json
import os

import praw

DEFAULT_SUBREDDIT_NAME = 'synthesizers'

CONTROVERSIALITY_THRESHHOLD = 0.5   # threshold to breach before actioning submission
TRENDING_THRESHOLD = 0.4            # threshold to breach before logging trending submission
MAX_SUBMISSIONS_TO_PROCESS = 50     # optimization: limit the number of submissions processed
MIN_COMMENTS_BEFORE_WARNING = 10    # ensure a minimum of top-level comments before actioning
MIN_SUBMISSION_AGE_TO_PROCESS = 60  # ensure a minimum submission age before actioning
DELETED_COMMENT_DEPTH = 2           # depth of deleted comment in tree to count as a negative signal


class SynthsControversialBot:
    def __init__(self, subreddit_name=DEFAULT_SUBREDDIT_NAME, dry_run=False):
        self.dry_run = dry_run

        self.reddit = praw.Reddit('SynthsControversialBot')
        self.subreddit = self.reddit.subreddit(subreddit_name)

        self.warning = self.read_text_file('controversial-warning.txt')

    def scan(self):
        for submission in self.subreddit.new(limit=MAX_SUBMISSIONS_TO_PROCESS):
            if (self.is_actionable(submission)
                    and self.calc_submission_age(submission) >= MIN_SUBMISSION_AGE_TO_PROCESS
                    and submission.num_comments >= MIN_COMMENTS_BEFORE_WARNING):
                self.process_submission(submission)

    def process_submission(self, submission):
        controversiality = self.calc_submission_controversiality(submission)

        if controversiality >= CONTROVERSIALITY_THRESHHOLD and not self.was_warned(submission):
            self.warn(submission, controversiality)
        elif controversiality >= TRENDING_THRESHOLD:
            self.log('Trending', submission, controversiality)

    # return a controversiality value between 0.0 and 1.0
    # where 0.0 is the least controversial and 1.0 is the most
    def calc_submission_controversiality(self, submission):
        comments = submission.comments
        comments.replace_more(limit=None)
        comments_list = comments.list()
        num_comments = len(comments_list)

        if num_comments == 0:
            return 0.0

        negative_signals = abs(submission.num_reports)

        for comment in comments_list:
            if comment.score <= 0:
                negative_signals += 1

            # check if top level comments were deleted
            if comment.removed and comment.depth <= DELETED_COMMENT_DEPTH:
                negative_signals += 1

            negative_signals += comment.controversiality
            negative_signals += abs(comment.num_reports)

        return min(negative_signals / num_comments, 1.0)

    def warn(self, submission, controversiality):
        if not self.dry_run:
            bot_comment = submission.reply(self.warning)
            bot_comment.mod.distinguish(sticky=True)
            bot_comment.mod.ignore_reports()

            submission.report('Heads up. This thread is trending controversial.')

        self.log('Warned', submission, controversiality)

    def was_warned(self, submission):
        warned = False

        if len(submission.comments) > 0:
            first_comment = submission.comments[0]
            warned = (first_comment.distinguished == 'moderator'  # don't collide with other mods or mod bots
                      or first_comment.author.name == self.reddit.config.username)

        return warned

    @ staticmethod
    def is_actionable(submission):
        return not any([
            submission.distinguished == 'moderator',
            submission.approved,
            submission.removed,
            submission.locked])

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

    def log(self, message, submission, controversiality):
        is_dry_run = '*' if self.dry_run is True else ''
        name = type(self).__name__
        now = datetime.datetime.now()
        print(f'{is_dry_run}[{name}][{now}] {message}: "{submission.title}" '
              f'({controversiality:.2f}) ({submission.id})')


def lambda_handler(event=None, context=None):
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    bot = SynthsControversialBot(subreddit_name=subreddit_name, dry_run=dry_run)
    bot.scan()


if __name__ == '__main__':
    lambda_handler()
