# EduByte AI 🎓⚡

### *The Unified, Graph-Based Adaptive Learning Engine via Web and WhatsApp.*

EduByte AI is an omni-channel, low-bandwidth adaptive learning platform designed for Nigerian students preparing for high-stakes examinations (WAEC, JAMB, NECO). It transforms unstructured materials (PDFs, notes) into dynamic learning workflows, tracks progress through an underlying dependency knowledge graph, and introduces cross-subject prerequisite gating.

---

## 🛠️ Unified Database Architecture (PostgreSQL)

To maximize performance within a unified system, EduByte AI avoids third-party graph or separate vector database nodes. We leverage **PostgreSQL** as an all-in-one data layer:
1. **Relational Engine:** Manages mandatory authentication, user profiles, and module completion tracking.
2. **Knowledge Graph Model:** Formed using self-referential adjacency relational tables, parsed via Python's `NetworkX` library to determine module locking/unlocking conditions.
3. **Vector Vector Engine (`pgvector`):** Stores chunked embeddings of past questions and textbook materials to run localized RAG loops.

---

## 🧭 System Interaction Flow & Pydantic Orchestration

Every user payload routed through our FastAPI Gateway evaluates the conversation context history against a polymorphic Pydantic JSON validator. The system enforces that the LLM response must match one of three execution schemas:

                [User Input / History Matrix]
                           │
                           ▼
                [FastAPI Engine Gateway]
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     [FOLLOW_UP]   [COURSE_GENERATION] [PRACTICE_QUIZ]
     Strict text    Full modules map,    10-20 interactive
    clarification   definitions, and    questions mapped to
      questions      progress gates      RAG source documents

---

## ✨ Core Features

* **🕸️ Graph-Based Prerequisite Checkpoints:** EduByte tracks cross-course knowledge. If you complete a Python syntax course inside a backend track, the system remembers it when you switch to Machine Learning. If a student attempts to skip ahead, the engine injects a 20-question challenge gate. If failed, the system locks advanced modules and re-routes the student to a refresher concept.
* **📱 Dual Endpoint Availability:** Full interactive graphical dashboard layout on the web interface, transitioning into interactive menu tree options over the WhatsApp Engine interface.
* **📦 Storage Efficiency:** Incorporates advanced vector compression frameworks (inspired by TurboQuant configurations) to reduce localized embedding storage demands within deployment endpoints.

---

## 💻 Technical Stack

* **Backend:** FastAPI (Asynchronous Python API gateway execution)
* **Data Layers:** PostgreSQL (`pgvector`, JSONB tracking schemas)
* **AI Tooling Frameworks:** LlamaIndex (Structured data extractors, PropertyGraph indices) + Gemini 3 Flash / Groq API
* **Frontend:** Next.js (TailwindCSS, React Flow node engine interface)
* **Omni-Channel Layer:** WhatsApp Business API integration wrappers

---

## 🚀 Rapid Local Setup

### Setup Database & Server Runtime
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Ensure pgvector is active on your Postgres instance
uvicorn main:app --reload