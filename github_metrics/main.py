import argparse
import dataclasses
import datetime
import json
import logging
import os
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Iterator, Optional

import pandas as pd
import requests
from dateutil.parser import parse as parse_datetime

from github_metrics import __title__

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PullRequest:
    title: str
    url: str
    created_at: datetime.datetime
    merged_at: datetime.datetime
    created_to_merged_minutes: int


def safe_filename(s: str, max_length: int = 64) -> str:
    short_hash = sha256(s.encode()).hexdigest()[:7]
    safe_str = re.sub(r'[^A-Za-z0-9_\-\.]', '_', s).strip('_')[:max_length]
    return f'{safe_str}--{short_hash}'


def github_api_list(url: str, token: str, cache_path: Path) -> Iterator[dict]:
    # Read cache
    path = cache_path / (safe_filename(url) + '.json')
    if path.is_file():
        logger.info('Reading %s from cache', url)
        with path.open('r') as f:
            data = json.load(f)
            items = data['items']
            next_url = data['next_url']
    else:
        # Fetch
        logger.info('Fetching %s', url)
        r = requests.get(
            url,
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {token}',
            },
        )
        r.raise_for_status()

        # Parse response
        items = r.json()
        m = re.search(r'<(?P<url>[^<]+)>; rel="next"', r.headers['Link'])
        next_url = m.group('url') if m else None

        # Write cache
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w') as f:
            data = {'items': items, 'next_url': next_url}
            json.dump(data, f)

    # Yield items
    yield from items

    # Continue with next page
    if next_url:
        yield from github_api_list(next_url, token, cache_path)


def fetch_pull_requests(
    owner: str, repo: str, token: str, cache_path: Path
) -> Iterator[PullRequest]:
    for item in github_api_list(
        f'https://api.github.com/repos/{owner}/{repo}/pulls?state=closed',
        token,
        cache_path,
    ):
        pull_request = transform_pull_request_item(item)
        if pull_request:
            yield pull_request


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
        merged_at=merged_at,
        created_to_merged_minutes=create_to_merge_minutes,
    )


def calc_stats_daily(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            'created_daily': df.groupby(
                [pd.Grouper(key='created_at', freq='D')]
            )['created_at'].count(),
            'merged_daily': df.groupby(
                [pd.Grouper(key='merged_at', freq='D')]
            )['merged_at'].count(),
            'created_to_merged_minutes_daily': df.groupby(
                [pd.Grouper(key='merged_at', freq='D')]
            )['created_to_merged_minutes'].mean(),
        }
    )


def calc_stats_weekly(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            'created_weekly': df.groupby(
                [pd.Grouper(key='created_at', freq='W')]
            )['created_at'].count(),
            'merged_weekly': df.groupby(
                [pd.Grouper(key='merged_at', freq='W')]
            )['merged_at'].count(),
            'created_to_merged_minutes_weekly': df.groupby(
                [pd.Grouper(key='merged_at', freq='W')]
            )['created_to_merged_minutes'].mean(),
        }
    )


def main():
    parser = argparse.ArgumentParser(prog=__title__)
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable debugging output'
    )
    parser.add_argument(
        '-c',
        '--cache',
        help='Cache directory path',
        type=Path,
        required=True,
    )
    parser.add_argument('--owner', help='Repository owner', required=True)
    parser.add_argument('--repo', help='Repository name', required=True)
    parser.add_argument(
        '-d',
        '--data',
        nargs='?',
        type=argparse.FileType('w'),
        default=sys.stdout,
    )
    parser.add_argument(
        '--stats-daily', nargs='?', type=argparse.FileType('w')
    )
    parser.add_argument(
        '--stats-weekly', nargs='?', type=argparse.FileType('w')
    )

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(
            stream=sys.stderr, level=logging.INFO, format='%(message)s'
        )

    token = os.environ.get('ACCESS_TOKEN')
    if not token:
        raise Exception('Missing ACCESS_TOKEN environment variable')

    pull_requests = fetch_pull_requests(
        args.owner, args.repo, token, args.cache
    )
    df = pd.DataFrame(dataclasses.asdict(pr) for pr in pull_requests)
    df.to_csv(
        args.data,
        index_label='created_at',
        columns=[
            'title',
            'url',
            'created_at',
            'merged_at',
            'created_to_merged_minutes',
        ],
    )

    if args.stats_daily:
        df_stats_daily = calc_stats_daily(df)
        df_stats_daily.to_csv(
            args.stats_daily,
            index_label='date',
            columns=[
                'created_daily',
                'merged_daily',
                'created_to_merged_minutes_daily',
            ],
            date_format='%Y-%m-%d',
        )

    if args.stats_weekly:
        df_stats_weekly = calc_stats_weekly(df)
        df_stats_weekly.to_csv(
            args.stats_weekly,
            index_label='date',
            columns=[
                'created_weekly',
                'merged_weekly',
                'created_to_merged_minutes_weekly',
            ],
            date_format='%Y-%m-%d',
        )


if __name__ == '__main__':
    main()
