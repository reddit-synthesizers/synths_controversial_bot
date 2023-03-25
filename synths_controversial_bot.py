import datetime
import os

import nltk
import praw
from nltk.sentiment import SentimentIntensityAnalyzer

DEFAULT_CLIENT_ID = 'SynthsControversialBot'
DEFAULT_SUBREDDIT_NAME = 'synthesizers'


# ratio of negative to positve comment to breach before warning a submission
CONTROVERSIAL_THRESHOLD = 0.33
# ratio of negative to positve comment to breach before logging a trending submission
TRENDING_THRESHOLD = 0.25

# optimization: limit the number of submissions processed
MAX_SUBMISSIONS_TO_PROCESS = 50
# optimization: ensure a minimum of top-level comments before processing
MIN_TOP_LEVEL_COMMENTS_BEFORE_PROCESSING = 10
# optimization: ensure a minimum of total comments before processing
MIN_TOTAL_COMMENTS_BEFORE_PROCESSING = 30
# ensure a minimum submission age, in minutes, before processing
MIN_SUBMISSION_AGE_TO_PROCESS = 60

# lower threshold to breach to consider a comment negative
NEGATIVE_SENTIMENT_THRESHOLD = -0.5


class SynthsControversialBot:
    def __init__(self, client_id=DEFAULT_CLIENT_ID, subreddit_name=DEFAULT_SUBREDDIT_NAME, dry_run=False):
        self.dry_run = dry_run

        self.reddit = praw.Reddit(client_id)
        self.subreddit = self.reddit.subreddit(subreddit_name)

        self.analyzer = SentimentIntensityAnalyzer()

        self.warning = self.read_text_file('controversial-warning.txt')

    def scan(self):
        for submission in self.subreddit.new(limit=MAX_SUBMISSIONS_TO_PROCESS):
            if self.should_process(submission):
                self.process_submission(submission)

    def process_submission(self, submission):
        polarity_ratio = self.calc_submission_polarity_ratio(submission)

        if polarity_ratio >= CONTROVERSIAL_THRESHOLD and not self.was_warned(submission):
            self.warn(submission, polarity_ratio)
        elif polarity_ratio >= TRENDING_THRESHOLD and not self.was_warned(submission):
            self.print_message('Trending', submission, polarity_ratio)

    def should_process(self, submission):
        return not (
            submission.distinguished == 'moderator' or
            submission.approved or
            submission.removed or
            submission.locked or
            self.calc_submission_age(submission) < MIN_SUBMISSION_AGE_TO_PROCESS or
            submission.num_comments < MIN_TOTAL_COMMENTS_BEFORE_PROCESSING or
            len(submission.comments) < MIN_TOP_LEVEL_COMMENTS_BEFORE_PROCESSING  # slow, so check last
        )

    # returns the ratio of negative to positive comments across a submission
    # where 0.0 is the least negative and 1.0 is the most
    def calc_submission_polarity_ratio(self, submission):
        submission.comments.replace_more(limit=None)
        num_negative_comments = sum(self.calc_comment_polarity(comment)
                                    for comment in submission.comments.list())
        return num_negative_comments / submission.num_comments

    # calculates comment polarity (negative or positive)
    # 1 for negative and 0 for positive
    def calc_comment_polarity(self, comment):
        return 1 if (
            comment.num_reports != 0 or
            comment.score <= 0 or
            comment.controversiality != 0 or
            self.calc_comment_sentiment(comment) <= NEGATIVE_SENTIMENT_THRESHOLD
        ) else 0

    # determine the average sentiment of the comment body as a collection of sentences
    # see: https://github.com/vaderSentiment/vaderSentiment
    def calc_comment_sentiment(self, comment):
        sentences = nltk.sent_tokenize(comment.body)
        return sum(self.analyzer.polarity_scores(sentence)['compound']
                   for sentence in sentences) / len(sentences)

    def warn(self, submission, controversiality):
        if not self.dry_run:
            bot_comment = submission.reply(self.warning)
            bot_comment.mod.distinguish(sticky=True)
            bot_comment.mod.ignore_reports()

            submission.report('Heads up. This thread is trending controversial.')

        self.print_message('Warned', submission, controversiality)

    def was_warned(self, submission):
        warned = False

        if len(submission.comments) > 0:
            first_comment = submission.comments[0]
            warned = (first_comment.distinguished == 'moderator'  # don't collide with other mods or mod bots
                      or first_comment.author.name == self.reddit.config.username)

        return warned

    def print_message(self, message, submission, controversiality):
        is_dry_run = '*' if self.dry_run is True else ''
        name = type(self).__name__
        now = datetime.datetime.now()
        print(f'{is_dry_run}[{name}][{now}] {message}: "{submission.title}" '
              f'({controversiality:.2f}) ({submission.id})')

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


def lambda_handler(event=None, context=None):
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    client_id = os.environ['client_id'] if 'client_id' in os.environ else DEFAULT_CLIENT_ID
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    bot = SynthsControversialBot(client_id=client_id, subreddit_name=subreddit_name, dry_run=dry_run)
    bot.scan()


if __name__ == '__main__':
    lambda_handler()
