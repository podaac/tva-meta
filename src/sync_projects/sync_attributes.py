import os
import requests
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sync_attributes")

GITHUB_API = "https://api.github.com/graphql"

# Get authentication token
token = os.environ.get("GITHUB_TOKEN")
if not token:
    raise RuntimeError("GITHUB_TOKEN is not set")

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# Get configuration from environment variables
SOURCE_PROJECT_NUMBER = int(os.environ.get("SOURCE_PROJECT_NUMBER", "68"))
TARGET_PROJECT_NUMBER = int(os.environ.get("TARGET_PROJECT_NUMBER", "74"))
ORG = "podaac"
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "").split("/")[1] if "/" in os.environ.get("GITHUB_REPOSITORY", "") else ""
REPO_OWNER = os.environ.get("GITHUB_REPOSITORY", "").split("/")[0] if "/" in os.environ.get("GITHUB_REPOSITORY", "") else ""

# Fields to synchronize
FIELDS_TO_SYNC = {"Status": "Status", "Estimate": "Estimate", "Sprint":"Iteration"}


def graphql(query, variables=None):
    """Execute a GraphQL query against the GitHub API"""
    response = requests.post(
        GITHUB_API,
        headers=HEADERS,
        json={"query": query, "variables": variables or {}},
    )
    response.raise_for_status()
    return response.json().get("data", {})



def get_project_id(project_number, org=None):
    """Get the ID of a GitHub Project based on its number"""

    query = f"""
    query($owner: String!, $number: Int!) {{
      organization(login: $owner) {{
        projectV2(number: $number) {{
          id
        }}
      }}
    }}
    """

    try:
        result = graphql(query, {"owner": ORG, "number": project_number})
        logger.debug(result)
        if not result or not result.get("organization", {}).get("projectV2", {}).get("id"):
            logger.error(f"Could not find project {project_number} for organization {ORG}")
            return None

        project_id = result["organization"]["projectV2"]["id"]
        logger.info(f"Found project ID: {project_id}")
        return project_id
    except Exception as e:
        logger.error(f"Error fetching project ID: {e}")
        raise


def get_project_fields(project_id):
    """Get all field definitions for a project"""
    logger.info(f"Getting fields for project {project_id}")

    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2Field {
                id
                name
                dataType
              }
              ... on ProjectV2IterationField {
                id
                name
                dataType
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                dataType
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """

    try:
        result = graphql(query, {"projectId": project_id})
        fields = result["node"]["fields"]["nodes"]
        logger.info(f"Found {len(fields)} fields")
        return fields
    except Exception as e:
        logger.error(f"Error fetching project fields: {e}")
        raise


def get_project_items(project_id):
    """Get all items in the project with their field values"""
    logger.info(f"Getting items for project {project_id}")

    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100) {
            nodes {
              id
              fieldValues(first: 50) {
                nodes {
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                        id
                      }
                    }
                  }
                  ... on ProjectV2ItemFieldDateValue {
                    date
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                        id
                      }
                    }
                  }
                  ... on ProjectV2ItemFieldNumberValue {
                    number
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                        id
                      }
                    }
                  }
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                        id
                      }
                    }
                  }
                  ... on ProjectV2ItemFieldIterationValue {
                    title
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                        id
                      }
                    }
                  }
                }
              }
              content {
                ... on Issue {
                  id
                  number
                  title
                  repository {
                    name
                    owner {
                      login
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    try:
        result = graphql(query, {"projectId": project_id})
        items = result["node"]["items"]["nodes"]
        logger.info(f"Found {len(items)} items")
        return items
    except Exception as e:
        logger.error(f"Error fetching project items: {e}")
        raise


def find_matching_items(source_items, target_items):
    """Find matching items between two projects based on issue number and repository"""
    logger.info("Finding matching items between projects")
    matches = []

    for source_item in source_items:
        # Skip items that aren't issues
        if not source_item.get("content") or source_item["content"].get("__typename") != "Issue":
            continue

        source_issue = source_item["content"]

        # Find the same issue in target project
        for target_item in target_items:
            if not target_item.get("content") or target_item["content"].get("__typename") != "Issue":
                continue

            target_issue = target_item["content"]

            # Match based on issue number and repository
            if (target_issue["number"] == source_issue["number"] and
                target_issue["repository"]["name"] == source_issue["repository"]["name"] and
                target_issue["repository"]["owner"]["login"] == source_issue["repository"]["owner"]["login"]):

                matches.append({
                    "sourceItem": source_item,
                    "targetItem": target_item
                })
                break

    logger.info(f"Found {len(matches)} matching items")
    return matches


def find_field_by_name(fields, field_name):
    """Find a field by name in a list of fields"""
    for field in fields:
        if field.get("name", "").lower() == field_name.lower():
            return field
    return None


def find_option_by_name(field, option_name):
    """Find a select option by name"""
    if not field.get("options") or not isinstance(field["options"], list):
        return None

    for option in field["options"]:
        if option.get("name", "").lower() == option_name.lower():
            return option
    return None


def update_field_value(project_id, item_id, field_id, field, value):
    """Update a field value"""
    field_type = field.get("dataType", "").upper()

    variables = {
        "projectId": project_id,
        "itemId": item_id,
        "fieldId": field_id
    }

    # Handle different field types
    if field_type == "SINGLE_SELECT":
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """
        variables["optionId"] = value

    elif field_type == "NUMBER":
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $number: Float!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { number: $number }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """
        variables["number"] = float(value)

    elif field_type == "ITERATION":
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $iterationId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { iterationId: $iterationId }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """
        variables["iterationId"] = value

    elif field_type == "TEXT":
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $text: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { text: $text }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """
        variables["text"] = value

    else:
        logger.error(f"Unsupported field type: {field_type}")
        return False

    try:
        graphql(mutation, variables)
        return True
    except Exception as e:
        logger.error(f"Error updating field value: {e}")
        return False


def sync_project_attributes():
    """Main function to synchronize project attributes"""
    logger.info("Starting synchronization process")

    # Get project IDs
    source_project_id = get_project_id(SOURCE_PROJECT_NUMBER, ORG)
    target_project_id = get_project_id(TARGET_PROJECT_NUMBER, ORG)

    if not source_project_id or not target_project_id:
        logger.error("Could not find one of the projects. Check project numbers and organization names.")
        return 1

    # Get fields for both projects
    source_fields = get_project_fields(source_project_id)
    target_fields = get_project_fields(target_project_id)

    # Get items for both projects
    source_items = get_project_items(source_project_id)
    target_items = get_project_items(target_project_id)

    # Find matching items
    matches = find_matching_items(source_items, target_items)

    # Sync field values for each match
    logger.info("Syncing field values")
    sync_count = 0

    for match in matches:
        source_item = match["sourceItem"]
        target_item = match["targetItem"]

        # Get issue details for logging
        issue_number = source_item["content"].get("number", "unknown")
        issue_title = source_item["content"].get("title", "unknown")

        # Process each field to sync
        for src_field_name, target_field_name in FIELDS_TO_SYNC.items():
            # Find the field in source project
            source_field = find_field_by_name(source_fields, src_field_name)
            if not source_field:
                logger.warning(f"Field '{src_field_name}' not found in source project, skipping")
                continue

            # Find the field in target project
            target_field = find_field_by_name(target_fields, target_field_name)
            if not target_field:
                logger.warning(f"Field '{target_field_name}' not found in target project, skipping")
                continue

            # Find the value in source item
            source_value = None
            field_value_type = None

            for node in source_item["fieldValues"]["nodes"]:
                if node.get("field", {}).get("name", "").lower() == src_field_name.lower():
                    if "text" in node:
                        source_value = node["text"]
                        field_value_type = "text"
                    elif "number" in node:
                        source_value = node["number"]
                        field_value_type = "number"
                    elif "name" in node:
                        source_value = node["name"]
                        field_value_type = "name"
                    elif "title" in node:
                        source_value = node["title"]
                        field_value_type = "title"
                    break

            if source_value is None:
                logger.info(f"No value for field '{src_field_name}' in issue #{issue_number}, skipping")
                continue

            # For single select fields, need to find the option ID in target field
            if field_value_type == "name":
                option_name = source_value
                target_option = find_option_by_name(target_field, option_name)

                if not target_option:
                    logger.warning(f"Option '{option_name}' not found in target field '{target_field_name}', skipping")
                    continue

                source_value = target_option["id"]

            # Update the target field
            logger.info(f"Updating '{target_field_name}' for issue #{issue_number} '{issue_title}' in target project")
            success = update_field_value(
                target_project_id,
                target_item["id"],
                target_field["id"],
                target_field,
                source_value
            )

            if success:
                sync_count += 1
                logger.info(f"Successfully updated '{target_field_name}' for issue #{issue_number}")
            else:
                logger.warning(f"Failed to update '{target_field_name}' for issue #{issue_number}")

    logger.info(f"Synchronization complete. Updated {sync_count} field values.")
    return 0


if __name__ == "__main__":
    sys.exit(sync_project_attributes())