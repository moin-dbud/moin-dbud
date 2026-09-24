"""
Fetches all the stats needed for the bento card from the GitHub API.

Requires an environment variable GH_TOKEN (a PAT with `read:user` and
`repo` scopes if you want private contributions counted) or falls back
to the default GITHUB_TOKEN provided inside Actions (public data only).
"""
import os
import sys
import datetime
import requests

GITHUB_GRAPHQL = "https://api.github.com/graphql"
GITHUB_REST = "https://api.github.com"


def _token():
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        sys.exit("ERROR: set GH_TOKEN (or GITHUB_TOKEN) as an env var / secret.")
    return tok


def _headers():
    return {"Authorization": f"bearer {_token()}"}


def gql(query, variables):
    resp = requests.post(
        GITHUB_GRAPHQL, json={"query": query, "variables": variables}, headers=_headers()
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    createdAt
    followers { totalCount }
    pullRequests(states: [OPEN, MERGED, CLOSED]) { totalCount }
    repositoriesContributedTo(
      includeUserRepositories: true
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
    ) { totalCount }
  }
}
"""

STARS_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, after: $cursor) {
      totalCount
      nodes { stargazerCount }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

CONTRIBUTIONS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""


def fetch_profile(login):
    data = gql(PROFILE_QUERY, {"login": login})
    return data["user"]


def fetch_total_stars(login):
    cursor = None
    total = 0
    contributed_to_forks_tracked = 0
    while True:
        data = gql(STARS_QUERY, {"login": login, "cursor": cursor})
        repos = data["user"]["repositories"]
        total += sum(n["stargazerCount"] for n in repos["nodes"])
        if repos["pageInfo"]["hasNextPage"]:
            cursor = repos["pageInfo"]["endCursor"]
        else:
            break
    return total


def fetch_all_contribution_days(login, created_at_iso):
    """Loops year-by-year (GraphQL caps each window at ~1 year) and returns
    a flat, date-sorted list of {date, count} plus lifetime commit total."""
    created = datetime.datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)

    all_days = {}
    total_commits = 0
    year_start = created
    while year_start < now:
        year_end = min(year_start + datetime.timedelta(days=365), now)
        data = gql(
            CONTRIBUTIONS_QUERY,
            {
                "login": login,
                "from": year_start.strftime("%Y-%m-%dT00:00:00Z"),
                "to": year_end.strftime("%Y-%m-%dT23:59:59Z"),
            },
        )
        cc = data["user"]["contributionsCollection"]
        total_commits += cc["totalCommitContributions"]
        for week in cc["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                all_days[day["date"]] = day["contributionCount"]
        year_start = year_end

    sorted_days = [{"date": d, "count": all_days[d]} for d in sorted(all_days)]
    return sorted_days, total_commits


def compute_streaks(sorted_days):
    """Longest streak ever, and current streak ending today/yesterday."""
    longest = 0
    longest_range = (None, None)
    cur = 0
    cur_start = None
    prev_date = None

    for entry in sorted_days:
        d = datetime.date.fromisoformat(entry["date"])
        if entry["count"] > 0:
            if prev_date is not None and (d - prev_date).days == 1:
                cur += 1
            else:
                cur = 1
                cur_start = d
            if cur > longest:
                longest = cur
                longest_range = (cur_start, d)
            prev_date = d
        else:
            cur = 0
            prev_date = None

    # current streak = trailing run touching today or yesterday
    today = datetime.date.today()
    current = 0
    current_start = None
    for entry in reversed(sorted_days):
        d = datetime.date.fromisoformat(entry["date"])
        if d > today:
            continue
        if entry["count"] > 0:
            current += 1
            current_start = d
        else:
            if d in (today, today - datetime.timedelta(days=1)) and current == 0:
                continue  # today not committed yet, don't break the streak
            break

    return {
        "longest": longest,
        "longest_from": longest_range[0].isoformat() if longest_range[0] else None,
        "longest_to": longest_range[1].isoformat() if longest_range[1] else None,
        "current": current,
        "current_from": current_start.isoformat() if current_start else None,
    }


def collect_all(login):
    profile = fetch_profile(login)
    stars = fetch_total_stars(login)
    days, total_commits = fetch_all_contribution_days(login, profile["createdAt"])
    streaks = compute_streaks(days)
    total_contributions = sum(d["count"] for d in days)

    return {
        "login": login,
        "followers": profile["followers"]["totalCount"],
        "pull_requests": profile["pullRequests"]["totalCount"],
        "contributed_to": profile["repositoriesContributedTo"]["totalCount"],
        "total_stars": stars,
        "total_commits": total_commits,
        "total_contributions": total_contributions,
        "streaks": streaks,
        "calendar": days,  # last ~365 days is what we render
    }


if __name__ == "__main__":
    import json as _json

    login = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_LOGIN")
    print(_json.dumps(collect_all(login), indent=2)[:2000])
