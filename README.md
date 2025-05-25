# 🧠 Autonomous Reasoning AI Agent

## 🎯 Project Summary

This repository showcases an autonomous AI agent designed to demonstrate advanced reasoning, memory, planning, and interaction. Built using Python and key libraries such as **LangChain**, **OpenAI**, and **Streamlit**, this agent supports interactive user communication with reflective capabilities and persistent memory.

This submission aligns with the assessment requirements for the AI Agent assignment.

---

## 📅 Submission Overview

- **🎥 YouTube Short (under 60s)**: [🔗 Link Here](https://youtube.com/shorts/your_video_link)
- **💻 GitHub Repository**: [🔗 This Repository](https://github.com/yourusername/ai-agent-assignment)

---

## ✅ Assessment Criteria Breakdown

| Criterion | How This Project Meets It |
|----------|----------------------------|
| **Problem Definition & Motivation** | The agent is designed to simulate cognitive reasoning and memory recall—helpful in tasks like tutoring, research, and decision support. |
| **Creativity & Usefulness** | The agent reflects on its own responses, uses memory (FAISS), and calls tools dynamically. |
| **Technical Implementation** | Clean modular code using LangChain, OpenAI, and Streamlit. Demonstrates looped reasoning and tool use. |
| **Video Clarity** | YouTube Short clearly presents agent behavior, tool use, memory usage, and interaction cycle. |
| **Presentation Quality** | Professional-quality video, code organization, and visual flowchart included below. |

---

## 🧩 Agent Workflow Diagram

```mermaid
graph TD
    A[User Input via Streamlit] --> B[agent.py: Initialize LangChain Agent]
    B --> C{Need External Info?}
    C -- Yes --> D[tools.py: Use Tools (e.g., Search)]
    C -- No --> E[Internal Reasoning]
    D --> F[Reflect on Output]
    E --> F
    F --> G[memory.py: Store in FAISS Memory]
    G --> H[Display Final Answer in Streamlit]
