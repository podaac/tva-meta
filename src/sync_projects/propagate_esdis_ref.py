import os
import sys
import json
import requests

GITHUB_API_URL = "https://api.github.com/graphql"
TOKEN = os.environ.get("PROJECTS_TOKEN")
PROJECT_ID = os.environ.get("PROJECT_ID", "PVT_kwDOAVayxs4BKQLN")
FIELD_ID = os.environ.get("FIELD_ID", "PVTF_lADOAVayxs4BKQLNzg8wxNg")


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

def get_parent_issue(issue_node_id):
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
    result = get_github_graphql(query, variables, TOKEN)
    print('Parent Data:', json.dumps(result, indent=2))
    return result


def extract_esdis_ref(parent_issue):

    try:
        parent_items = parent_issue["data"]["node"]["projectItems"]["nodes"]
        parent_item = next((i for i in parent_items if i["project"]["id"] == PROJECT_ID), None)
        print('Parent Item:', json.dumps(parent_item, indent=2))
        parent_value = None
        if parent_item:
            for v in parent_item["fieldValues"]["nodes"]:
                if v.get("field") and v["field"].get("id") == FIELD_ID:
                    parent_value = v.get("text")
                    break
        print(f"Parent PCESA Ref: {parent_value}")
        return parent_value
    except Exception as e:
        print(f"Error processing parent data: {e}", file=sys.stderr)
        sys.exit(1)

def extract_sub_issues(parent_issue):
    try:
        sub_issues = parent_issue["data"]["node"]["subIssues"]["nodes"]
        sub_issue_ids = [issue["id"] for issue in sub_issues]
        print(f"Sub-issue IDs: {sub_issue_ids}")
        return sub_issue_ids
    except Exception as e:
        print(f"Error processing sub-issues: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # Read required environment variables

    issue_node_id = os.environ.get("ISSUE_NODE_ID")

    if not TOKEN or not issue_node_id:
        print("Missing PROJECTS_TOKEN or ISSUE_NODE_ID.", file=sys.stderr)
        sys.exit(1)

    parent_issue = get_parent_issue(issue_node_id)
    esdis_ref = extract_esdis_ref(parent_issue)

    if not esdis_ref:
        print("No ESDIS reference found on parent issue.", file=sys.stderr)
        sys.exit(1)

    sub_issue_ids = extract_sub_issues(parent_issue)
    for sub_issue_id in sub_issue_ids:
        print(f"Sub-issue ID: {sub_issue_id} should be updated with ESDIS Ref: {esdis_ref}")


if __name__ == "__main__":
    main()

