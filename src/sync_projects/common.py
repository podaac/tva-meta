import os
import requests

def graphql(query, variables=None, api_url=None, token=None):
    """Execute a GraphQL query against the GitHub API"""
    if api_url is None:
        api_url = os.environ.get("GITHUB_API", "https://api.github.com/graphql")
    if token is None:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PROJECTS_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN or PROJECTS_TOKEN is not set")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        api_url,
        headers=headers,
        json={"query": query, "variables": variables or {}},
    )
    response.raise_for_status()
    return response.json().get("data", {})
