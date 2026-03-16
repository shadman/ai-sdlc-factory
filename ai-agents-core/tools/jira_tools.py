from crewai_tools import BaseTool
from atlassian import Jira  # Make sure to pip install atlassian-python-api
import os

class JiraCommentTool(BaseTool):
    name: "JiraCommentTool"
    description: "Use this tool to post a progress update or completion comment to a Jira ticket."

    def _run(self, issue_key: str, comment: str) -> str:
        jira = Jira(
            url=os.getenv("JIRA_DOMAIN"),
            username=os.getenv("JIRA_USERNAME"),
            password=os.getenv("JIRA_API_TOKEN"),
            cloud=True
        )
        jira.issue_add_comment(issue_key, comment)
        return f"Successfully posted comment to {issue_key}"