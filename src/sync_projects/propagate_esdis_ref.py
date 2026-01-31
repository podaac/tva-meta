import os
import sys
import json
import requests

GITHUB_API_URL = "https://api.github.com/graphql"

def get_github_graphql(query, variables, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        GITHUB_API_URL,
        headers=headers,
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    return response.json()

def main():
    # Read required environment variables
    token = os.environ.get("PROJECTS_TOKEN")
    issue_node_id = os.environ.get("ISSUE_NODE_ID")
    project_id = os.environ.get("PROJECT_ID", "PVT_kwDOAVayxs4BKQLN")
    field_id = os.environ.get("FIELD_ID", "PVTF_lADOAVayxs4BKQLNzg8wxNg")
    if not token or not issue_node_id:
        print("Missing PROJECTS_TOKEN or ISSUE_NODE_ID.", file=sys.stderr)
        sys.exit(1)

    query = '''
    query ($id: ID!) {
      node(id: $id) {
        ... on Issue {
          id
          projectItems(first: 10) {
            nodes {
              id
              project {
                 ... on ProjectV2 {
                   id
                  }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    field {
                      ... on ProjectV2FieldCommon {
                        id 
                      }
                    }
                  }
                }
              }
            }
          }
          subIssues(first: 50) {
            nodes {
              id
              repository { nameWithOwner }
            }
          }
        }
      }
    }
    '''
    variables = {"id": issue_node_id}
    result = get_github_graphql(query, variables, token)
    print('Parent Data:', json.dumps(result, indent=2))
    try:
        parent_items = result["data"]["node"]["projectItems"]["nodes"]
        parent_item = next((i for i in parent_items if i["project"]["id"] == project_id), None)
        print('Parent Item:', json.dumps(parent_item, indent=2))
        parent_value = None
        if parent_item:
            for v in parent_item["fieldValues"]["nodes"]:
                if v.get("field") and v["field"].get("id") == field_id:
                    parent_value = v.get("text")
                    break
        print(f"Parent PCESA Ref: {parent_value}")
    except Exception as e:
        print(f"Error processing parent data: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

