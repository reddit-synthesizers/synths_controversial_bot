import datetime
import json
import math
import os
import praw

from flashtext import KeywordProcessor
from praw.models import MoreComments


DEFAULT_SUBREDDIT_NAME = 'synthesizers'

MIN_COMMENTS_TO_WARN = 10
MIN_SUBMISSION_AGE_TO_WARN = 60
SCORE_THRESHHOLD = 10.0
MAX_SUBMISSIONS_TO_PROCESS = 50


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
        # for submission in self.subreddit.search('title:behringer', sort='new', limit=50):
        for submission in self.subreddit.new(limit=MAX_SUBMISSIONS_TO_PROCESS):
            self.process_submission(submission)

    def process_submission(self, submission):
        score = 0
        score += self.get_title_score(submission)
        score += self.get_body_score(submission)

        age = self.get_submission_age(submission)

        if (score > 0
                and age >= MIN_SUBMISSION_AGE_TO_WARN
                and submission.num_comments >= MIN_COMMENTS_TO_WARN
                and not submission.distinguished == 'moderator'
                and not submission.approved
                and not submission.removed
                and not submission.locked):

            score += self.get_user_reports_count(submission)
            score += self.get_comments_score(submission)
            score = round(score, 2)

            if score >= SCORE_THRESHHOLD:
                self.warn(submission, score)
            elif score >= SCORE_THRESHHOLD / 1.5:
                self.log('Trending', submission, score)
            else:
                self.log('Info', submission, score)

    def get_title_score(self, submission):
        score = 0

        for keyword in self.keyword_processor.extract_keywords(submission.title):
            score += self.keywords[keyword]

        return score

    def get_body_score(self, submission):
        score = 0

        for keyword in self.keyword_processor.extract_keywords(submission.selftext):
            score += self.keywords[keyword]

        return score

    def get_comments_score(self, submission):
        score = 0
        downvoted_comments = 0

        submission.comments.replace_more(limit=None)

        for comment in submission.comments.list():
            if comment.removed:
                score += self.weights['removed']

            score += comment.controversiality * self.weights['controversial']
            score += self.get_user_reports_count(comment) * self.weights['reported']

            if comment.score <= 0:
                downvoted_comments += 1

            for keyword in self.keyword_processor.extract_keywords(comment.body):
                score += self.keywords[keyword]

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
    def get_user_reports_count(obj):
        count = len(obj.user_reports)

        if hasattr(obj, 'user_reports_dismissed'):
            count += len(obj.user_reports_dismissed)

        return count

    @staticmethod
    def get_submission_age(submission):
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
        print(f'{is_dry_run}[{name}][{now}] {message}: (score={score}) \'{submission.title}\' ({submission.id})')


def lambda_handler(event=None, context=None):
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    bot = SynthsControversialBot(subreddit_name=subreddit_name, dry_run=dry_run)
    bot.scan()


if __name__ == '__main__':
    lambda_handler()
