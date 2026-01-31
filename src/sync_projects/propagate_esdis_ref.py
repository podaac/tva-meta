import os
import sys
import json
import requests
from .common import graphql

PROJECT_ID = os.environ.get("PROJECT_ID", "PVT_kwDOAVayxs4BKQLN")
FIELD_ID = os.environ.get("FIELD_ID", "PVTF_lADOAVayxs4BKQLNzg8wxNg")


def get_issue(issue_node_id):
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
    result = graphql(query, variables)
    print('Parent Data:', json.dumps(result, indent=2))
    return result


def extract_esdis_ref(parent_issue):

    try:
        parent_items = parent_issue["node"]["projectItems"]["nodes"]
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


def add_esdis_ref(issue_node_id, esdis_ref):
    query = '''
            mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
                      updateProjectV2ItemFieldValue(
                        input: {
                          projectId: $projectId
                          itemId: $itemId
                          fieldId: $fieldId
                          value: { text: $value }
                        }
                      ) {
                        projectV2Item { id }
                      }
                    }
    '''

    variables = {
        "projectId": PROJECT_ID,
        "itemId": issue_node_id,
        "fieldId": FIELD_ID,
        "value": esdis_ref
      }
    result = graphql(query, variables)
    return result




def main():
    # Read required environment variables

    issue_node_id = os.environ.get("ISSUE_NODE_ID")

    parent_issue = get_issue(issue_node_id)
    esdis_ref = extract_esdis_ref(parent_issue)

    if not esdis_ref:
        print("No ESDIS reference found on parent issue.", file=sys.stderr)
        sys.exit(1)

    sub_issue_ids = extract_sub_issues(parent_issue)
    for sub_issue_id in sub_issue_ids:
        print(f"Sub-issue ID: {sub_issue_id} should be updated with ESDIS Ref: {esdis_ref}")
        sub_issue = get_issue(sub_issue_id)
        print("child issue node:", json.dumps(sub_issue, indent=2))
        child_esdis_ref = extract_esdis_ref(sub_issue)
        if child_esdis_ref:
            print(f"Sub-issue {sub_issue_id} already has an ESDIS reference. Change manually.")
            continue

        # Here you would add the mutation to update the sub-issue with the ESDIS ref
        add_esdis_ref(sub_issue_id, esdis_ref)
        print(f"Added ESDIS reference to sub-issue {sub_issue_id}.")



if __name__ == "__main__":
    main()

