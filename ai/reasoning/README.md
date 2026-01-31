🤖 Terraform AI Review Platform (Production-Grade)

A centralized, reusable AI-powered Terraform PR reviewer that behaves like a 20–30 year Staff / Principal Engineer.

This platform analyzes Terraform plans, understands intent and context, applies enterprise policy packs, performs security & risk reasoning, and can PASS / WARN / BLOCK pull requests automatically.

🚀 Designed for real-world production use across dozens or hundreds of Terraform repositories.

🔑 Why this exists

Traditional Terraform checks:

Validate syntax

Enforce formatting

Apply static rules

But real outages happen due to:

Blast radius

Networking mistakes

Security exposure

Poor rollout strategy

Context-less approvals

This platform answers:

“Is this change safe — given what it’s doing, where it’s running, and how it’s deployed?”

🧠 What this platform does

✔ Reads Terraform plan output, not just code
✔ Understands intent (bootstrap vs risky change vs security hardening)
✔ Applies pattern-based reasoning (cloud-agnostic)
✔ Uses policy packs (network, identity, security, platform)
✔ Differentiates good PRs vs bad PRs
✔ Produces human-quality explanations
✔ Enforces PASS / WARN / BLOCK in PRs
✔ Works across all Azure services (present & future)

⚠️ LLMs are used only for explanation, never for decision making.

🏗 Architecture Overview
Consumer Terraform Repo
│
│  Pull Request
│
▼
Reusable GitHub Workflow (this platform)
│
├─ Terraform Plan
├─ Context Enrichment
├─ Risk & Policy Engine
├─ AI Explanation
├─ PR Comment
└─ PR Enforcement (PASS / WARN / BLOCK)

📁 Repository Structure (IMPORTANT)
ai-terraform-reviewer-platform/
│
├── ai/
│   ├── context/                # Terraform plan → enriched semantic context
│   │   └── enrich.py
│   │
│   ├── knowledge/              # Stable knowledge (NO LLM)
│   │   ├── knowledge_loader.py
│   │   ├── risk_patterns.json
│   │   ├── service_capabilities.json
│   │   ├── security_severity.json
│   │
│   ├── policies/               # Enterprise policy packs
│   │   ├── policy_packs.json
│   │   └── policy_loader.py
│   │
│   ├── reasoning/              # Core intelligence
│   │   ├── review.py           # Risk, policy & decision engine
│   │   ├── intent_detector.py
│   │   ├── llm_enrichment.py
│   │   └── post_comment.py
│   │
│   └── memory/                 # (Optional) historical learning
│       └── memory_store.py
│
├── .github/
│   └── workflows/
│       └── terraform-ai-review.yml   # Reusable workflow (PR enforcement)
│
├── requirements.txt
└── README.md

🧩 Key Design Principles
1️⃣ Pattern-based (not service-based)

No hardcoding Azure services

New services work automatically

Patterns like network_boundary, blast_radius, public_exposure

2️⃣ Policy ≠ Violation

A policy match does not automatically mean a violation.

Example:

Create-only networking → allowed

Security hardening → rewarded

Destructive networking → escalated

This avoids false positives.

3️⃣ LLMs never decide

LLMs are used only to:

Explain reasoning

Improve human readability

All decisions are:

Deterministic

Auditable

Explainable

4️⃣ Central platform, many repos

One platform repo

Many consumer Terraform repos

Zero duplication

Zero secrets in platform repo

🧪 How a PR is evaluated

Terraform plan is generated

Plan is converted to JSON

Context is enriched (resources, patterns, intent)

Risk score is calculated

Policy packs are evaluated

Security severity is applied

Final decision is made:

PASS

WARN

BLOCK

AI explanation is generated

PR comment is posted

PR is blocked if required

🛡 PR Decisions Explained
Decision	Meaning
PASS	Safe to merge
WARN	Risky — human review recommended
BLOCK	Dangerous — merge prevented

Blocking happens only when:

Critical security exposure

High-risk change in production

🧑‍💻 Consumer Repository Requirements

Each Terraform repo that wants AI review must have:

1️⃣ Workflow (calls this platform)
uses: <org>/ai-terraform-reviewer-platform/.github/workflows/terraform-ai-review.yml@main

2️⃣ Repo-level config
.ai-reviewer.yaml


Example:

environment: dev

enabled_policies:
  - network_policy
  - identity_policy
  - security_baseline

3️⃣ Secrets (in consumer repo only)

AZURE_CREDENTIALS

AZURE_OPENAI_KEY

AZURE_OPENAI_ENDPOINT

AZURE_OPENAI_DEPLOYMENT

✅ Good PR vs Bad PR (Real Behavior)
✅ Good PR

Create-only infrastructure

No public exposure

Gated compute

Security tightening

➡️ PASS + LGTM

❌ Bad PR

Public IPs

Open NSGs

Destructive network changes

Multiple risky changes

➡️ BLOCK + clear explanation
