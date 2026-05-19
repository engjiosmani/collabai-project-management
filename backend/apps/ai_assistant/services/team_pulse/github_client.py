"""Fetch recent commits from GitHub REST API (per-workspace PAT)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

GITHUB_API = 'https://api.github.com'


def fetch_commits_for_repo(
    *,
    access_token: str,
    repo: str,
    since: datetime,
    author_login: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return commits for owner/repo since `since`.
    repo format: "owner/name"
    """
    if not access_token or '/' not in repo:
        return []

    owner, name = repo.split('/', 1)
    params = {'since': since.strftime('%Y-%m-%dT%H:%M:%SZ')}
    if author_login:
        params['author'] = author_login.strip()

    url = f'{GITHUB_API}/repos/{owner}/{name}/commits?{urllib.parse.urlencode(params)}'
    request = urllib.request.Request(
        url,
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'CollabAI-TeamPulse',
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')[:300]
        logger.warning('GitHub API error for %s: %s %s', repo, exc.code, body)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning('GitHub fetch failed for %s: %s', repo, exc)
        return []

    if not isinstance(data, list):
        return []

    commits = []
    for item in data:
        commit = item.get('commit') or {}
        author = (item.get('author') or {}).get('login') or (
            (commit.get('author') or {}).get('name')
        )
        commits.append(
            {
                'sha': (item.get('sha') or '')[:7],
                'message': (commit.get('message') or '').split('\n')[0][:200],
                'author_login': author,
                'committed_at': (commit.get('committer') or commit.get('author') or {}).get('date'),
                'repo': repo,
                'url': item.get('html_url'),
            }
        )
    return commits


def fetch_member_commits(
    *,
    access_token: str,
    repos: list[str],
    since: datetime,
    github_login: str,
) -> list[dict[str, Any]]:
    if not github_login:
        return []
    all_commits: list[dict[str, Any]] = []
    for repo in repos:
        all_commits.extend(
            fetch_commits_for_repo(
                access_token=access_token,
                repo=repo,
                since=since,
                author_login=github_login,
            )
        )
    all_commits.sort(key=lambda c: c.get('committed_at') or '', reverse=True)
    return all_commits
