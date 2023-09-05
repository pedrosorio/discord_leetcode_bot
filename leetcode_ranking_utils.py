import bisect
from collections import Counter
from math import ceil
import json
import requests

RANKING_URL_BASE = "https://leetcode.com/contest/api/ranking/{contest_name}"
RANKING_URL_PAGE = RANKING_URL_BASE + '/?pagination={page}&region=global' 
USERS_PER_PAGE = 25

def get_num_users(contest_name):
    res = requests.get(RANKING_URL_BASE.format(contest_name=contest_name))
    count_users = json.loads(res.content)['user_num']
    return count_users

def get_num_pages(contest_name):
    return ceil(get_num_users(contest_name) / USERS_PER_PAGE)

def get_ranking_page(contest_name, page, debug_print=False):
    res = requests.get(RANKING_URL_PAGE.format(contest_name=contest_name, page=page))
    if debug_print:
        print(page, res.status_code)
    return json.loads(res.content)['total_rank']

def get_count_per_country(contest_name, start_page=1, num_pages=None, country_counter=None, only_positive_score=True, debug_print=False):
    if country_counter is None:
        country_counter = Counter()
    if num_pages is None:
        num_pages = get_num_pages(contest_name)

    for page in range(start_page, start_page+num_pages):
        for row in get_ranking_page(contest_name, page, debug_print):
            if only_positive_score and row['score'] == 0:
                return country_counter 
            country_counter[row['country_name']] += 1

    if debug_print:
        print(sum(country_counter.values()))
    return country_counter 

class BinarySearchManually:
    def binary_search_num_users_with_positive_score(contest_name, max_page, debug_print=False):
        max_nonzero = 0 
        min_page = 1
        while min_page <= max_page:
            page = (min_page + max_page) // 2
            rows = get_ranking_page(contest_name, page, debug_print)
            if rows[0]['score'] == 0:
                max_page = page-1
                continue
            if rows[-1]['score'] == 0:
                return max(row['rank'] for row in rows if row['score'] > 0)
            max_nonzero = max(max_nonzero, rows[-1]['rank'])
            min_page = page+1
        return max_nonzero

# Just for funsies, use the built-in bisect module to perform binary search on 
# the scores to find the find the last non-zero
# This does use more memory to instantiate a list of scores for all participants
# in the contest, but it's an interesting way to use the Python stdlib
class BinarySearchWithBisect:
    class FetchableScore:
        def __init__(self, rank):
            self.rank = rank
            self.score = None

    def binary_search_num_users_with_positive_score(contest_name, max_page, debug_print=False):
        scores = [BinarySearchWithBisect.FetchableScore(i) for i in range(max_page * USERS_PER_PAGE + 1)]
        
        def key_function(fetchable_score: BinarySearchWithBisect.FetchableScore):
            if fetchable_score.score is None:
                for row in get_ranking_page(contest_name, ceil(fetchable_score.rank / USERS_PER_PAGE), debug_print=debug_print):
                    scores[row['rank']].score = row['score']
            # negative because the scores are descending by rank
            return -fetchable_score.score

        return bisect.bisect_left(scores, 0, key=key_function) - 1

def get_num_users_with_positive_score(contest_name, binary_search_class=BinarySearchManually, debug_print=False):
    res = requests.get(RANKING_URL_BASE.format(contest_name=contest_name))
    count_users = json.loads(res.content)['user_num']
    max_page = ceil(count_users / 25)
    return binary_search_class.binary_search_num_users_with_positive_score(contest_name, max_page, debug_print)
    