# 🤖 AI Terraform Reviewer for Azure

An AI-powered Terraform Pull Request reviewer that analyzes Azure infrastructure
changes and provides **risk-aware, explainable feedback** directly on GitHub PRs.

---

## 🚀 What This Does

On every Pull Request:
1. Runs `terraform plan`
2. Converts plan to JSON
3. Enriches context (shared infra, network, environment)
4. Applies AI reasoning
5. Posts a **human-style review comment** on the PR

---

## 🧠 What Makes This Different

✔ Understands Azure-specific risks  
✔ Detects shared infrastructure blast radius  
✔ Escalates for production changes  
✔ Provides confidence scoring  
✔ Suggests actionable next steps  
✔ Fully automated via GitHub Actions  

---

## 🏗️ Architecture

