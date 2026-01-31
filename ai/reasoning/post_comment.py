import json
import os
from github import Github


def main():
    # Resolve ai_review.json from workspace root
    base_dir = os.getcwd()
    review_path = os.path.join(base_dir, "ai_review.json")

    if not os.path.exists(review_path):
        raise FileNotFoundError(f"ai_review.json not found at {review_path}")

    with open(review_path, "r") as f:
        review = json.load(f)

    pr_number = os.environ.get("PR_NUMBER")
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")

    if not pr_number or not github_token or not repo_name:
        raise ValueError("PR_NUMBER, GITHUB_TOKEN, or GITHUB_REPOSITORY is missing")

    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))

    # ----------------------------
    # LLM SECTION (NEW)
    # ----------------------------
    llm_text = review.get("llm_explanation")
    llm_section = ""

    if llm_text and "unavailable" not in llm_text.lower():
        llm_section = f"""
---

## 🧠 LLM Risk Explanation (AI)

{llm_text}
"""

    # ----------------------------
    # PR COMMENT BODY
    # ----------------------------
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
{llm_section}
"""

    pr.create_issue_comment(body)
    print("✅ AI review comment (with LLM explanation) posted successfully")


if __name__ == "__main__":
    main()
