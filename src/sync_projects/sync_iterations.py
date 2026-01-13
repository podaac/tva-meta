import os
import requests

GITHUB_API = "https://api.github.com/graphql"

HEADERS = {
    "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
    "Content-Type": "application/json",
}

ORG = os.environ["ORG"]
SOURCE_PROJECT_NUMBER = int(os.environ["SOURCE_PROJECT_NUMBER"])
TARGET_PROJECT_NUMBER = int(os.environ["TARGET_PROJECT_NUMBER"])


def graphql(query, variables=None):
    r = requests.post(
        GITHUB_API,
        headers=HEADERS,
        json={"query": query, "variables": variables or {}},
    )
    r.raise_for_status()
    return r.json()["data"]


def get_project(project_number):
    query = """
    query ($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          id
          fields(first: 50) {
            nodes {
              ... on ProjectV2IterationField {
                id
                name
                configuration {
                  iterations {
                    id
                    title
                    startDate
                    duration
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    data = graphql(query, {"org": ORG, "number": project_number})
    project = data["organization"]["projectV2"]

    iteration_field = next(
        f for f in project["fields"]["nodes"]
        if f and f.get("configuration")
    )

    return project["id"], iteration_field


def sync_iterations():
    _, source_field = get_project(SOURCE_PROJECT_NUMBER)
    target_project_id, target_field = get_project(TARGET_PROJECT_NUMBER)

    source_iterations = source_field["configuration"]["iterations"]
    target_iterations = target_field["configuration"]["iterations"]

    existing_titles = {it["title"] for it in target_iterations}

    mutation = """
    mutation ($fieldId: ID!, $projectId: ID!, $title: String!, $start: Date!, $duration: Int!) {
      addProjectV2Iteration(
        input: {
          projectId: $projectId
          fieldId: $fieldId
          title: $title
          startDate: $start
          duration: $duration
        }
      ) {
        iteration {
          id
        }
      }
    }
    """

    for it in source_iterations:
        if it["title"] in existing_titles:
            continue

        print(f"Creating iteration: {it['title']}")

        graphql(
            mutation,
            {
                "projectId": target_project_id,
                "fieldId": target_field["id"],
                "title": it["title"],
                "start": it["startDate"],
                "duration": it["duration"],
            },
        )


if __name__ == "__main__":
    sync_iterations()