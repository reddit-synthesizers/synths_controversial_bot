import datetime
import functools
import json
import math
import os

import praw
from flashtext import KeywordProcessor

DEFAULT_SUBREDDIT_NAME = 'synthesizers'

SCORE_THRESHHOLD = 7.0
MAX_SUBMISSIONS_TO_PROCESS = 50
MIN_COMMENTS_TO_WARN = 10
MIN_SUBMISSION_AGE_TO_PROCESS = 60


class Score():
    def __init__(self, title=0.0, body=0.0, reports=0.0, comments=0.0):
        self.title = title
        self.body = body
        self.reports = reports
        self.comments = comments

    @property
    def total(self):
        return self.title + self.body + self.reports + self.comments

    def __str__(self):
        return (f'total:{self.total:.2f}, title:{self.title:.2f}, body:{self.body:.2f}, '
                f'reports:{self.reports:.2f}, comments:{self.comments:.2f}')


class SynthsControversialBot:
    def __init__(self, subreddit_name=DEFAULT_SUBREDDIT_NAME, dry_run=False):
        self.dry_run = dry_run

        self.reddit = praw.Reddit('SynthRulesBot')
        self.subreddit = self.reddit.subreddit(subreddit_name)

        self.warning = self.read_text_file('controversial-warning.txt')
        self.keywords = self.read_json_file('controversial-keywords.json')
        self.weights = self.read_json_file('controversial-weights.json')

        self.keyword_processor = KeywordProcessor()
        self.keyword_processor.add_keywords_from_list(list(self.keywords))

    def scan(self):
        for submission in self.subreddit.new(limit=MAX_SUBMISSIONS_TO_PROCESS):
            if (self.is_actionable(submission)
                    and self.calc_submission_age(submission) >= MIN_SUBMISSION_AGE_TO_PROCESS
                    and submission.num_comments >= MIN_COMMENTS_TO_WARN):
                self.process_submission(submission)

    def process_submission(self, submission):
        title_score = self.calc_title_score(submission)

        if title_score > 0.0:
            score = Score(
                title_score,
                self.calc_body_score(submission),
                self.calc_user_reports_count(submission),
                self.calc_comments_score(submission))

            if score.total >= SCORE_THRESHHOLD:
                self.warn(submission, score)
            elif score.total >= SCORE_THRESHHOLD / 1.5:
                self.log('Trending', submission, score)

    def calc_title_score(self, submission):
        keywords = self.keyword_processor.extract_keywords(submission.title)
        return functools.reduce(lambda x, y: x + self.keywords[y], keywords, 0)

    def calc_body_score(self, submission):
        keywords = self.keyword_processor.extract_keywords(submission.selftext)
        return functools.reduce(lambda x, y: x + self.keywords[y], keywords, 0)

    def calc_comments_score(self, submission):
        score = 0
        downvoted_comments = 0

        submission.comments.replace_more(limit=None)

        for comment in submission.comments.list():
            if comment.removed:
                score += self.weights['removed']

            score += comment.controversiality * self.weights['controversial']
            score += self.calc_user_reports_count(comment) * self.weights['reported']

            if comment.score <= 0:
                downvoted_comments += 1

            for keyword in self.keyword_processor.extract_keywords(comment.body):
                score += self.keywords[keyword]

        if submission.num_comments > 0:
            score += math.ceil(downvoted_comments / submission.num_comments * self.weights['downvoted'])

        return score

    def warn(self, submission, score):
        if not self.was_warned(submission):
            if not self.dry_run:
                bot_comment = submission.reply(self.warning)
                bot_comment.mod.distinguish(sticky=True)
                bot_comment.mod.ignore_reports()

                submission.report('Heads up. This thread is trending controversial.')

            self.log('Warned', submission, score)

    def was_warned(self, submission):
        warned = False

        if len(submission.comments) > 0:
            first_comment = submission.comments[0]
            warned = (first_comment.distinguished == 'moderator'  # don't collide with other mods or mod bots
                      or first_comment.author.name == self.reddit.user.me())

        return warned

    @staticmethod
    def is_actionable(submission):
        return (not submission.distinguished == 'moderator'
                and not submission.approved
                and not submission.removed
                and not submission.locked)

    @staticmethod
    def calc_user_reports_count(obj):
        count = len(obj.user_reports)

        if hasattr(obj, 'user_reports_dismissed'):
            count += len(obj.user_reports_dismissed)

        return count

    @staticmethod
    def calc_submission_age(submission):
        now = datetime.datetime.now()
        created = datetime.datetime.fromtimestamp(submission.created_utc)
        age = now - created

        return age.total_seconds() / 60

    @staticmethod
    def read_text_file(filename):
        with open(filename, encoding='utf-8') as file:
            text = file.read()

        return text

    @staticmethod
    def read_json_file(filename):
        with open(filename, encoding='utf-8') as file:
            data = json.load(file)

        return data

    def log(self, message, submission, score):
        is_dry_run = '*' if self.dry_run is True else ''
        name = type(self).__name__
        now = datetime.datetime.now()
        print(f'{is_dry_run}[{name}][{now}] {message}: "{submission.title}" ({score}) ({submission.id})')


def lambda_handler(event=None, context=None):
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    bot = SynthsControversialBot(subreddit_name=subreddit_name, dry_run=dry_run)
    bot.scan()


if __name__ == '__main__':
    lambda_handler()
