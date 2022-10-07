import argparse
import csv
import datetime
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import IO, Iterable, Iterator, Optional

import requests
from dateutil.parser import parse as parse_datetime

from github_metrics import __title__

logger = logging.getLogger(__name__)


@dataclass
class PullRequest:
    title: str
    url: str
    created_at: datetime.datetime
    created_to_merged_minutes: int


def github_api_list(url: str, token: str) -> Iterator[dict]:
    logger.info('Fetching %s', url)
    r = requests.get(
        url,
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {token}',
        },
    )
    r.raise_for_status()
    m = re.search(r'<(?P<url>[^<]+)>; rel="next"', r.headers['Link'])
    next_url = m.group('url') if m else None
    yield from r.json()
    if next_url:
        yield from github_api_list(next_url, token)


def transform_pull_request_item(item: dict) -> Optional[PullRequest]:
    if not item['merged_at']:
        return None
    created_at = parse_datetime(item['created_at'])
    merged_at = parse_datetime(item['merged_at'])
    create_to_merge_td = merged_at - created_at
    create_to_merge_minutes = round(create_to_merge_td.total_seconds() / 60)
    return PullRequest(
        title=item['title'],
        url=item['html_url'],
        created_at=created_at,
        created_to_merged_minutes=create_to_merge_minutes,
    )


def fetch_pull_requests(
    owner: str, repo: str, token: str
) -> Iterator[PullRequest]:
    for item in github_api_list(
        f'https://api.github.com/repos/{owner}/{repo}/pulls?state=closed',
        token,
    ):
        pull_request = transform_pull_request_item(item)
        if pull_request:
            yield pull_request


def write_pull_requests_as_csv(pull_requests: Iterable[PullRequest], f: IO):
    writer = csv.writer(f, lineterminator='\n')
    writer.writerow(
        ('title', 'url', 'created_at', 'created_to_merged_minutes')
    )
    for pull_request in pull_requests:
        writer.writerow(
            (
                pull_request.title,
                pull_request.url,
                pull_request.created_at.isoformat(),
                pull_request.created_to_merged_minutes,
            )
        )


def main():
    parser = argparse.ArgumentParser(prog=__title__)
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable debugging output'
    )
    parser.add_argument('--owner', help='Repository owner', required=True)
    parser.add_argument('--repo', help='Repository name', required=True)
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout
    )

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(
            stream=sys.stderr, level=logging.INFO, format='%(message)s'
        )

    token = os.environ.get('ACCESS_TOKEN')
    if not token:
        raise Exception('Missing ACCESS_TOKEN environment variable')

    pull_requests = fetch_pull_requests(args.owner, args.repo, token)
    write_pull_requests_as_csv(pull_requests, args.outfile)


if __name__ == '__main__':
    main()
