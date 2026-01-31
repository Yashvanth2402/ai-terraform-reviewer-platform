import json
import os
import sys
from github import Github


def main():
    # ✅ Always resolve paths safely
    base_dir = os.getcwd()
    review_path = os.path.join(base_dir, "ai_review.json")

    if not os.path.exists(review_path):
        raise FileNotFoundError(f"ai_review.json not found at {review_path}")

    with open(review_path, "r") as f:
        review = json.load(f)

    pr_number = os.environ.get("PR_NUMBER")
    github_token = os.environ.get("GITHUB_TOKEN")

    if not pr_number or not github_token:
        raise ValueError("PR_NUMBER or GITHUB_TOKEN is missing")

    g = Github(github_token)
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
    pr = repo.get_pull(int(pr_number))

    body = f"""
## 🤖 Terraform AI Review

**Environment:** {review.get("environment")}
**Risk Level:** 🚨 **{review.get("risk_level")}**
**Confidence:** {review.get("confidence")}

### 🔍 Reasons
{chr(10).join(f"- {r}" for r in review.get("reasons", []))}

### 💬 Review Comments
{chr(10).join(f"- {c}" for c in review.get("review_comments", []))}

### ✅ Recommendations
{chr(10).join(f"- {rec}" for rec in review.get("recommendations", []))}
"""

    pr.create_issue_comment(body)
    print("✅ AI review comment posted successfully")


if __name__ == "__main__":
    main()
