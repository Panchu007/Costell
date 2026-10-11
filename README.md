# 📊 Costell
> **A constellation of signals that reveals your project's true cost.**

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

## 🎯 The Problem
Traditional cost estimation models (COCOMO, function points, story points) assume a human-only development team. In 2026, that assumption is broken. Modern software teams are AI-augmented, using Copilot, Cursor, and LLMs daily. Yet, no existing estimation tool captures the **AI Leverage Factor** or the new **AI infrastructure costs** (API calls, GPU compute, vector databases). 

IT projects still go over budget by **45% on average** because managers estimate with one risky number.

## 💡 The Solution
**Costell** is the first cost estimation engine designed specifically for the AI-native development era. 

You paste a project description (PRD), and Costell gives you a full budget breakdown (People, Tooling, Cloud/AI Infra) with a statistically calibrated confidence range (P50/P80/P90).

> **Analogy:** Think of Google Maps. It doesn't say "you'll arrive in exactly 30 minutes." It says "30 to 40 minutes, depending on traffic." Costell does that for project cost.

## ✨ Key Features
- **AI Leverage Factor (ALF):** A proprietary metric that quantifies how much AI actually accelerates specific development tasks.
- **LLM Scope Decomposition:** Automatically breaks PRDs into a Work Breakdown Structure (WBS).
- **ML Effort Prediction:** Uses CatBoost trained on historical project data (ISBSG, SEERA, Desharnais).
- **Honest Confidence Intervals:** Implements MAPIE Conformal Prediction for calibrated P50/P80/P90 ranges.
- **Explainable AI (XAI):** SHAP values show *exactly* why the estimate is what it is.
- **Scenario Planning:** "What if we add 2 senior devs?" or "What if we drop feature X?"
- **AI Advises, Models Decide:** The LLM never invents numbers. All costs are calculated by deterministic ML models and validated by Pydantic.

## 🏗️ Architecture
```mermaid
graph TD
    A[User PRD] --> B(LLM Scope Decomposer)
    B --> C[WBS Editor]
    C --> D{AI Leverage Engine}
    D --> E[Effort & Cost Engine]
    E --> F[Conformal Uncertainty MAPIE]
    F --> G[Scenario Planner]
    G --> H[Budget Report P50/P80/P90]
    