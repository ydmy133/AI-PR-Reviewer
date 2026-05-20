import hashlib
import hmac
import os
from typing import Optional

import requests
from fastapi import FastAPI, Header, HTTPException, Request
from github import Github

app = FastAPI(title="AI PR Reviewer")

DIFF_FILE_LABEL = "文件"
DIFF_STATUS_LABEL = "状态"
NO_DIFF_COMMENT = "AI Review: 本次 PR 未包含可审查的文本 Diff（可能都是二进制或空变更）。"
REVIEW_COMMENT_HEADER = "## 🤖 AI Code Review"
SYSTEM_PROMPT_TEMPLATE = """
你是资深代码审查专家，请审查以下 Pull Request 的代码 Diff。

你的审查目标：
1. 找出潜在 Bug（逻辑错误、边界条件、异常处理遗漏、并发问题等）
2. 找出安全风险（注入、鉴权、敏感信息泄露、权限控制不足等）
3. 提升可读性和可维护性（命名、结构、重复代码、注释与复杂度）

输出要求：
- 使用简洁、专业、可执行的中文建议
- 按“严重程度”分组：高 / 中 / 低
- 每条建议包含：问题、影响、建议修复方式
- 如果未发现明显问题，也要给出“总体评价”和可改进建议

以下是需要审查的代码 Diff：
{diff_content}
""".strip()


def _verify_webhook_signature(body: bytes, signature_256: Optional[str]) -> None:
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        return

    if not signature_256:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    expected_signature = "sha256=" + hmac.new(
        webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _build_diff_content(pull) -> str:
    parts = []
    for file in pull.get_files():
        if not file.patch:
            continue
        parts.append(
            f"{DIFF_FILE_LABEL}: {file.filename}\n{DIFF_STATUS_LABEL}: {file.status}\n```diff\n{file.patch}\n```"
        )
    return "\n\n".join(parts)


def _call_llm_for_review(diff_content: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(diff_content=diff_content)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "请根据要求输出完整评审结论，并优先给出可直接修改的建议。",
            },
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(default=None),
    x_hub_signature_256: Optional[str] = Header(default=None),
):
    body = await request.body()
    _verify_webhook_signature(body, x_hub_signature_256)

    payload = await request.json()

    if x_github_event != "pull_request":
        return {"message": "Ignored: not a pull_request event"}

    if payload.get("action") != "opened":
        return {"message": "Ignored: pull_request action is not opened"}

    repo_full_name = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not configured")

    github_client = Github(github_token)
    repo = github_client.get_repo(repo_full_name)
    pull = repo.get_pull(pr_number)

    diff_content = _build_diff_content(pull)
    if not diff_content:
        pull.create_issue_comment(NO_DIFF_COMMENT)
        return {"message": "No text diff found"}

    review_comment = _call_llm_for_review(diff_content)
    pull.create_issue_comment(f"{REVIEW_COMMENT_HEADER}\n\n{review_comment}")

    return {"message": "Review comment posted successfully", "pr": pr_number}


@app.get("/")
def health_check():
    return {"status": "ok"}
