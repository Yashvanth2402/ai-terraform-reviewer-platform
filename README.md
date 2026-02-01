# 🤖 Terraform AI Review Platform (Production-Grade)

A **centralized, reusable AI-powered Terraform Pull Request reviewer** that behaves like a **20–30 year Staff / Principal Engineer**.

This platform analyzes **Terraform plans**, understands **intent and blast radius**, applies **enterprise policy packs**, performs **security & risk reasoning**, and automatically **PASS / WARN / BLOCK** pull requests.

> 🚀 Built for **real-world production environments** running **dozens or hundreds of Terraform repositories**.

---

## 🔑 Why This Platform Exists

Traditional Terraform checks focus on:

- Syntax validation
- Formatting
- Static rule enforcement

But **real outages** happen due to:

- Massive blast radius
- Networking mistakes
- Security exposure
- Unsafe rollouts
- Context-less approvals

This platform answers the real question:

> **“Is this change safe — given what it’s doing, where it’s running, and how it’s deployed?”**

---

## 🧠 What This Platform Does

✔ Reads **Terraform plan output**, not just code  
✔ Understands **intent** (bootstrap vs risky vs security hardening)  
✔ Applies **pattern-based reasoning** (cloud-agnostic)  
✔ Enforces **enterprise policy packs**  
✔ Differentiates **good PRs vs bad PRs**  
✔ Produces **human-quality explanations**  
✔ Automatically enforces **PASS / WARN / BLOCK**  
✔ Works across **all Azure services (present & future)**  

> ⚠️ **LLMs are used only for explanation — never for decision making**

---

## 🏗 Architecture Overview

Consumer Terraform Repo
│
▼
Pull Request
│
▼
Reusable GitHub Workflow (This Platform)
├─ Terraform Plan
├─ Context Enrichment
├─ Risk & Policy Engine
├─ AI Explanation
├─ PR Comment
└─ PR Enforcement (PASS / WARN / BLOCK)


---

## 📁 Repository Structure

ai-terraform-reviewer-platform/
│
├── ai/
│ ├── context/ # Terraform plan → enriched semantic context
│ │ └── enrich.py
│ │
│ ├── knowledge/ # Stable knowledge (NO LLMs)
│ │ ├── knowledge_loader.py
│ │ ├── risk_patterns.json
│ │ ├── service_capabilities.json
│ │ └── security_severity.json
│ │
│ ├── policies/ # Enterprise policy packs
│ │ ├── policy_packs.json
│ │ └── policy_loader.py
│ │
│ ├── reasoning/ # Core intelligence
│ │ ├── review.py # Risk, policy & decision engine
│ │ ├── intent_detector.py
│ │ ├── llm_enrichment.py
│ │ └── post_comment.py
│ │
│ └── memory/ # (Optional) historical learning
│ └── memory_store.py
│
├── .github/
│ └── workflows/
│ └── terraform-ai-review.yml # Reusable PR enforcement workflow
│
├── requirements.txt
└── README.md


---

## 🧩 Core Design Principles

### 1️⃣ Pattern-Based (Not Service-Based)

- No hardcoding Azure services
- New services work automatically
- Uses patterns like:
  - `network_boundary`
  - `blast_radius`
  - `public_exposure`

---

### 2️⃣ Policy ≠ Violation

A policy match **does not automatically mean a violation**.

**Examples:**
- Create-only networking → ✅ Allowed
- Security hardening → ✅ Rewarded
- Destructive networking → 🚨 Escalated

This avoids false positives and alert fatigue.

---

### 3️⃣ LLMs Never Decide

LLMs are used **only** to:

- Explain reasoning
- Improve human readability

All decisions are:

- Deterministic
- Auditable
- Explainable

---

### 4️⃣ Central Platform, Many Repos

- One platform repository
- Many consumer Terraform repositories
- Zero duplication
- Zero secrets stored in platform repo

---

## 🧪 How a Pull Request Is Evaluated

1. Terraform plan is generated
2. Plan is converted to JSON
3. Context is enriched (resources, patterns, intent)
4. Risk score is calculated
5. Policy packs are evaluated
6. Security severity is applied
7. Final decision is made:
   - **PASS**
   - **WARN**
   - **BLOCK**
8. AI explanation is generated
9. PR comment is posted
10. PR is blocked automatically if required

---

## 🛡 PR Decision Model

| Decision | Meaning |
|--------|--------|
| **PASS** | Safe to merge |
| **WARN** | Risky — human review recommended |
| **BLOCK** | Dangerous — merge prevented |

🔒 **Blocking occurs only when:**
- Critical security exposure
- High-risk changes in production environments

---

## 🧑‍💻 Consumer Repository Requirements

Each Terraform repo must have:

### 1️⃣ Reusable Workflow

```yaml
uses: your-org/ai-terraform-reviewer-platform/.github/workflows/terraform-ai-review.yml@main
2️⃣ Repo-Level Configuration
.ai-reviewer.yaml

environment: dev

enabled_policies:
  - network_policy
  - identity_policy
  - security_baseline
3️⃣ Secrets (Stored in Consumer Repo Only)
AZURE_CREDENTIALS

AZURE_OPENAI_KEY

AZURE_OPENAI_ENDPOINT

AZURE_OPENAI_DEPLOYMENT

🔐 No secrets are ever stored in the platform repository

✅ Real-World Behavior
✅ Good PR
Create-only infrastructure

No public exposure

Gated compute

Security tightening

➡️ PASS + clear LGTM explanation

❌ Bad PR
Public IPs

Open NSGs

Destructive network changes

Multiple risky changes

➡️ BLOCK + precise, human-readable explanation
