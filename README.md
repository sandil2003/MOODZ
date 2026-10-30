# MOODZ 

<div align="center">
  <img src="moodz-frontend/public/favicon.ico" width="180" alt="MOODZ Logo" />
  
  # Your Personal AI Wellness Companion
  
  An intelligent mental health platform powered by modern multi-agent AI architectures, deterministic safety gating, and a privacy-first AgentOps observability & evaluation platform.

  [![Angular](https://img.shields.io/badge/Angular-21.0-DD0031?logo=angular)](https://angular.io/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blueviolet)](https://github.com/langchain-ai/langgraph)
  [![Google ADK](https://img.shields.io/badge/Google_ADK-2.13+-4285F4?logo=google)](https://github.com/google/adk)
  [![Arize Phoenix](https://img.shields.io/badge/Arize_Phoenix-AgentOps-orange?logo=apache)](https://github.com/Arize-ai/phoenix)
  [![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-OTel-blue?logo=opentelemetry)](https://opentelemetry.io/)
  [![DeepEval](https://img.shields.io/badge/DeepEval-AI_Evals-purple)](https://github.com/confident-ai/deepeval)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript)](https://www.typescriptlang.org/)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
  [![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4.1-38B2AC?logo=tailwindcss)](https://tailwindcss.com/)
  [![Azure](https://img.shields.io/badge/Azure-Cloud_Native-0078D4?logo=microsoftazure)](https://azure.microsoft.com/)
</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#️-system-architecture)
  - [End-to-End System Architecture Diagram](#end-to-end-system-architecture-diagram)
  - [AI Agent Architecture Diagram](#-ai-agent-architecture-diagram)
- [Tech Stack](#️-tech-stack)
- [AgentOps & Observability (Arize Phoenix)](#-agentops--observability-arize-phoenix)
  - [Live Phoenix Dashboard](#1-live-phoenix-dashboard)
  - [Inspecting Google ADK Tool Calls](#2-inspecting-google-adk-tool-calls)
  - [Token, Latency & Cost Tracking](#3-token-latency--cost-tracking)
  - [Human-in-the-Loop (HITL) Feedback](#4-human-in-the-loop-hitl-feedback)
- [Clinical Data Privacy & PII Scrubbing](#-clinical-data-privacy--pii-scrubbing)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Running with Docker (Recommended)](#running-with-docker-recommended)
  - [Running Locally](#running-locally-without-docker)
  - [Running Google ADK Agent UI](#running-google-adk-agent-ui)
- [Project Structure](#-project-structure)
- [AI Agents & Hybrid Orchestration](#-ai-agents--hybrid-orchestration)
  - [Mood Agent (Active)](#mood-agent-active)
  - [Google ADK Tool Bindings](#google-adk-tool-bindings)
  - [LangGraph StateGraph Engine](#langgraph-stategraph-engine)
  - [Fine-Tuned & Local Model Support](#fine-tuned--local-model-support)
- [Continuous Evaluation & Safety Gates](#-continuous-evaluation--safety-gates)
  - [100% Crisis Detection Recall Benchmark](#1-100-crisis-detection-recall-benchmark)
  - [DeepEval LLM-as-a-Judge Empathy Suite](#2-deepeval-llm-as-a-judge-empathy-suite)
  - [Automated CI/CD Quality Gates](#3-automated-cicd-quality-gates)
- [☁️ Azure Deployment Plan](#️-azure-deployment-plan)
- [API Documentation](#-api-documentation)
- [License](#-license)

---

## 🌟 Overview

**MOODZ** is a state-of-the-art mental wellness platform that bridges cutting-edge generative AI with compassionate human experience design. Built to provide empathetic conversational companion support, mood journaling, and cognitive insights, MOODZ combines **Google ADK** (Agent Development Kit) for multi-agent capabilities and **LangGraph StateGraph** for deterministic zero-latency safety gating, token streaming, and multi-tier contextual memory.

Crucially, MOODZ integrates an enterprise-grade, privacy-first **AgentOps platform**: all multi-step agent traces, Google ADK tool calls, Time-to-First-Token (TTFT) latencies, and token costs are monitored via a self-hosted **Arize Phoenix** server with automated **PII sanitization** and **DeepEval** evaluation gates.

### Active & Upcoming Agents
- **Mood Agent (Active)**: Empathetic AI companion with real-time SSE streaming, safety gates, sentiment analysis, episodic vector memory, and background profiling.
- **Journal Agent (In Development)**: Reflective thought-structuring and guided journaling with daily prompts.
- **Study Agent (In Development)**: Adaptive learning assistant for cognitive breakdown and study scheduling.

---

## ✨ Key Features

- **🛡️ Deterministic Zero-Latency Safety Gate**: Instantly flags crisis/self-harm signals with 0 token overhead and $<10\text{ms}$ deterministic response, short-circuiting immediately to verified 988 Lifeline resources.
- **🔍 Self-Hosted AgentOps & Observability**: Complete visibility into agent decision trees, Google ADK tool executions, and LLM token costs via **Arize Phoenix** running directly on your infrastructure with zero external data exposure.
- **🔒 Clinical PII/PHI Sanitization Middleware**: Sub-millisecond recursive redaction masking emails, phone numbers, SSNs, and financial identifiers before telemetry persistence.
- **🧠 Multi-Tier Context Memory**:
  - *Short-Term Memory*: In-memory conversation state backed by Redis.
  - *Long-Term Episodic Memory*: Semantic vector embeddings stored in Pinecone with cosine similarity search.
  - *User Fact Profile*: Persistent relational user insights and preferences stored in PostgreSQL.
- **⚡ Real-Time Streaming & WebSockets**: Server-Sent Events (SSE) for low-latency token streaming, supplemented by WebSocket live status channels.
- **🧪 Continuous Agent Evaluation**: Automated **DeepEval** and **LLM-as-a-Judge** suites validating response empathy, faithfulness, and clinical safety in CI/CD.
- **👍 Human-in-the-Loop (HITL) Feedback**: Frontend rating endpoints (`POST /api/moods/chat/feedback`) tagging traces directly in Phoenix for continuous model and prompt refinement.
- **🤖 Multi-Model & Custom LLM Flexibility**: Native support for Google Gemini 2.5 Flash, OpenAI GPT-4, and custom fine-tuned models (e.g., Qwen via LM Studio / Colab endpoints).
- **📊 Interactive Analytics Dashboard**: Track emotional trends over time, sentiment distribution, and conversation history.
- **🌓 Modern Glassmorphic UI**: Angular 21 with Signals, TailwindCSS v4, dark mode support, and full Markdown rendering.

---

## 🏛️ System Architecture

MOODZ adopts an asynchronous, modular microservices architecture designed for resilience, patient-data privacy, and real-time responsiveness.

### End-to-End System Architecture Diagram

```mermaid
graph TB
    %% Client Tier
    subgraph ClientTier ["1. Client Tier (Frontend)"]
        direction TB
        Browser["User Browser"]
        AngularApp["Angular 21 SPA<br/>(Signals, TailwindCSS 4, Dark UI)"]
        FeedbackUI["Human Feedback Controls<br/>(Thumbs Up/Down & Mood Correction)"]
        
        Browser <--> AngularApp
        AngularApp --- FeedbackUI
    end

    %% Gateway & Privacy Tier
    subgraph GatewayTier ["2. Application Gateway & Privacy Tier"]
        direction TB
        FastAPI["FastAPI Web Framework<br/>(Async ASGI / Uvicorn)"]
        Router["Router Layer<br/>(Auth, Chat, Mood, History, Feedback)"]
        PIIScrubber["PII Sanitizer Middleware<br/>(Sub-millisecond Recursive Redaction)"]
        OTelExporter["OpenTelemetry & OpenInference<br/>(OTLP Trace Exporter)"]
        
        FastAPI --> Router
        Router --> PIIScrubber
        PIIScrubber --> OTelExporter
    end

    %% Agent Execution Tier
    subgraph AgentTier ["3. Traced Agent Execution Engine"]
        direction TB
        SafetyGate["Deterministic Safety Gate (0ms)<br/>(crisis_detector.py)"]
        LangGraph["LangGraph Hybrid StateGraph<br/>(mood_graph.py)"]
        ADK["Google ADK Agent & Tools<br/>(mood_adk.py)"]
        
        LangGraph --> SafetyGate
        LangGraph --> ADK
    end

    %% Data & Memory Tier
    subgraph DataTier ["4. Data & Caching Tier"]
        direction LR
        Postgres[("PostgreSQL DB<br/>(Relational Users, Chat History, Facts)")]
        RedisClient[("Redis Cache<br/>(Active Sessions & Context Buffer)")]
        Pinecone[("Pinecone Vector DB<br/>(Episodic Semantic Embeddings)")]
    end

    %% Inference Tier
    subgraph AITier ["5. AI Inference Tier"]
        direction LR
        Gemini["Google Gemini 2.5 Flash<br/>(Primary Empathetic & Profiler LLM)"]
        OpenAI["OpenAI GPT Models<br/>(Alternative Inference)"]
        CustomLLM["Self-Hosted / Fine-Tuned Model<br/>(vLLM / LM Studio / Colab)"]
    end

    %% AgentOps Observability Platform
    subgraph OpsTier ["6. AgentOps Observability & Evaluation Platform (Docker)"]
        direction TB
        PhoenixServer["Arize Phoenix Server<br/>(Web UI :6006 | OTLP Collector :4317)"]
        TraceStore[("Phoenix Trace Database<br/>(Waterfall Traces, Latencies, Costs)")]
        EvalHarness["DeepEval & Pytest Benchmark Suite<br/>(Empathy, Faithfulness, Safety Evals)"]
        
        PhoenixServer --> TraceStore
        PhoenixServer --> EvalHarness
    end

    %% Connections
    AngularApp == "HTTP REST / SSE Stream / WS" ==> FastAPI
    FeedbackUI == "POST /api/moods/chat/feedback" ==> Router
    Router ==> LangGraph
    ADK == "Async SQLAlchemy" ==> Postgres
    ADK == "Key-Value State" ==> RedisClient
    ADK == "RAG Semantic Search" ==> Pinecone
    LangGraph == "Inference" ==> Gemini
    LangGraph == "Fallback / Alternate" ==> OpenAI
    LangGraph == "Local / Fine-Tuned" ==> CustomLLM
    
    OTelExporter -. "gRPC Port 4317 (OTLP)" .-> PhoenixServer
```

---

### 🤖 AI Agent Architecture Diagram

The diagram below details the **internal hybrid execution flow** of the Mood Agent, illustrating the fast foreground streaming path, background intelligence extraction, Google ADK tool bindings, and telemetry instrumentation:

```mermaid
flowchart TD
    subgraph InputTier ["1. User Ingress & Safety Gate"]
        UserMsg(["User Message"])
        SafetyGate{"Deterministic Safety Gate<br/>(crisis_detector.py)<br/>0ms | 0 Tokens"}
        CrisisResponse(["Immediate Crisis Intervention<br/>(988 Lifeline & Resources)"])
    end

    subgraph StateGraphEngine ["2. LangGraph Hybrid Orchestrator (mood_graph.py)"]
        direction TB
        
        subgraph ForegroundPath ["Fast Foreground Path (Streaming)"]
            ContextIngest["Context Ingestion Node<br/>(asyncio.gather Concurrent Retrieval)"]
            PromptAssembler["Empathetic System Prompt & Context Assembly"]
            CompanionStream["Streaming Companion LLM<br/>(astream Markdown Tokens)"]
            StreamOut(["Real-Time SSE Token Stream to User"])
        end

        subgraph BackgroundPath ["Asynchronous Background Path (Non-Blocking)"]
            ProfilerSubAgent["Clinical Profiler Sub-Agent<br/>(Structured Pydantic Extraction)"]
            FactExtract["Personal Fact Extraction"]
            MoodScoring["Sentiment & Score Rating (1-10)"]
        end
    end

    subgraph ADKTools ["3. Google ADK Tools & Memory Integration (mood_adk.py)"]
        direction LR
        RedisTool[("Redis Cache<br/>Short-Term History")]
        PineconeTool[("Pinecone Vector DB<br/>Episodic Semantic Memory")]
        PostgresTool[("PostgreSQL DB<br/>Relational Profile & Facts")]
    end

    subgraph TelemetryLayer ["4. AgentOps Telemetry Layer (@trace_tool / trace_span)"]
        SpanCollector["Spans, Latency (TTFT), Tool I/O & Scrubbed PII"]
        PhoenixSink[("Arize Phoenix Trace Server (:6006)")]
    end

    UserMsg --> SafetyGate
    SafetyGate -- "Crisis Triggered (100% Recall)" --> CrisisResponse
    SafetyGate -- "Safe" --> ContextIngest
    
    ContextIngest <--> RedisTool
    ContextIngest <--> PineconeTool
    ContextIngest <--> PostgresTool
    
    ContextIngest --> PromptAssembler --> CompanionStream --> StreamOut
    
    CompanionStream -. "Handoff Response" .-> ProfilerSubAgent
    ProfilerSubAgent --> FactExtract & MoodScoring
    FactExtract --> PostgresTool & PineconeTool
    MoodScoring --> PostgresTool
    
    SafetyGate -. Spans .-> SpanCollector
    ContextIngest -. Spans .-> SpanCollector
    CompanionStream -. TTFT & Tokens .-> SpanCollector
    ProfilerSubAgent -. Classification Spans .-> SpanCollector
    SpanCollector --> PhoenixSink
```

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Angular** | 21.0 | Signal-based reactive Single Page Application |
| **TypeScript** | 5.9 | Type-safe enterprise JavaScript |
| **TailwindCSS** | 4.1 | Modern glassmorphic styling with dark theme support |
| **RxJS** | 7.8 | Asynchronous reactive event streams |
| **ngx-markdown** | 21.0 | Fluid Markdown formatting in conversational bubbles |

### Backend & AI Orchestration
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | Latest | High-concurrency async Python ASGI framework |
| **Python** | 3.11+ | Core backend runtime (tested up to Python 3.14) |
| **LangGraph** | 0.2+ | StateGraph pipeline & conditional node orchestration |
| **Google ADK** | 2.13+ | Declarative multi-agent declarations and toolkits |
| **SQLAlchemy** | 2.0+ (Async) | Async ORM for relational user, chat, and fact storage |
| **Alembic** | Latest | Automated database schema migrations |
| **Celery** | Latest | Background task queue & scheduled worker jobs |
| **Pinecone** | Latest | Vector database for episodic long-term memory |
| **Redis** | 7+ | Session state store and real-time conversation buffering |
| **PostgreSQL** | 15+ | Relational database for accounts, sessions, and insights |

### AgentOps, Observability & Evaluation
| Technology | Version | Purpose |
|------------|---------|---------|
| **Arize Phoenix** | Latest | Self-hosted AgentOps observability, waterfall traces & cost analytics |
| **OpenTelemetry (OTel)** | 1.25+ | CNCF vendor-neutral distributed tracing protocol |
| **OpenInference** | Latest | GenAI semantic conventions for LangGraph & LangChain |
| **DeepEval** | 4.0+ | Production LLM-as-a-Judge, empathy validation & safety evals |
| **PII Scrubber** | Built-in | Sub-millisecond recursive redaction of sensitive clinical data |

---

## 🔍 AgentOps & Observability (Arize Phoenix)

MOODZ includes a full-featured, self-hosted **Arize Phoenix** platform, providing end-to-end visibility into every agent decision, tool execution, and LLM token cost.

```
                      ┌────────────────────────────────────────┐
                      │   Google ADK & LangGraph (MOODZ)       │
                      │   - Safety Gate & Context Ingestion    │
                      │   - Streaming Companion LLM            │
                      │   - Background Profiler Sub-Agent      │
                      └──────────────────┬─────────────────────┘
                                         │
                             Emits OpenTelemetry Spans
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │   AgentOps Layer (Arize Phoenix)       │
                      │   - Waterfall Execution Traces         │
                      │   - Scrubbed PII Tool Inspection       │
                      │   - Token Counts & Spend ($)           │
                      │   - Time-to-First-Token (TTFT) SLA     │
                      └────────────────────────────────────────┘
```

### 1. Live Phoenix Dashboard
Start the containerized Phoenix service:
```bash
docker compose up -d phoenix
```
Open **`http://localhost:6006`** in your browser to access:
- **Traces Tab**: Step-by-step waterfall execution trees of every user turn.
- **Spans Tab**: Flat, filterable table auditing individual tool calls and node transitions.
- **Projects View**: Aggregated token burn, latency percentiles (P50, P90, P99), and total spend.

### 2. Inspecting Google ADK Tool Calls
Every ADK tool (`check_crisis_tool`, `retrieve_user_context_tool`, `persist_user_facts_tool`, `persist_mood_entry_tool`) is wrapped with the `@trace_tool` decorator. Clicking a tool span in Phoenix reveals:
- **Execution Latency**: Exact millisecond runtime (e.g., `tool.duration_ms: 18.4ms`).
- **Sanitized Arguments**: Function arguments with all PII automatically masked.
- **Success / Exception State**: Exact exception stack traces in case of database or network timeouts.

### 3. Token, Latency & Cost Tracking
- **Time-to-First-Token (TTFT)**: Tracked on the `langgraph.astream_companion` span to guarantee streaming responsiveness ($<800\text{ms}$).
- **Token Attribution**: Prompt tokens, completion tokens, and model dollar costs are attributed to individual user sessions.

### 4. Human-in-the-Loop (HITL) Feedback
Users can rate companion responses (thumbs up/down) or provide corrected mood labels from the frontend. The backend logs this via:
- **Endpoint**: `POST /api/moods/chat/feedback`
- **Tracing Impact**: Feedback automatically tags the session trace in Phoenix, allowing developers to filter by `rating == -1` to inspect and fine-tune failing prompts.

---

## 🔒 Clinical Data Privacy & PII Scrubbing

Because MOODZ is a mental health companion, users frequently share sensitive trauma, names, contact numbers, or medical history. **Raw user data must never leak to observability logs.**

MOODZ includes an ultra-fast, recursive PII scrubber (`backend/app/core/pii_scrubber.py`) that operates with $<0.2\text{ms}$ latency:
- **Email Addresses**: `user@example.com` $\to$ `[REDACTED_EMAIL]`
- **Phone Numbers**: `(555) 234-5678` $\to$ `[REDACTED_PHONE]`
- **Social Security Numbers (SSN)**: `000-12-3456` $\to$ `[REDACTED_SSN]`
- **Credit Card Numbers**: `4111-2222-3333-4444` $\to$ `[REDACTED_CREDIT_CARD]`

All dictionaries, lists, and span attributes pass through `PIIScrubber.scrub_dict()` before being sent to the OTLP exporter.

---

## 🚀 Getting Started

### Prerequisites

Ensure you have installed:
- **Node.js** 18+ and `npm`
- **Python** 3.11+
- **Docker** & **Docker Compose** *(Recommended)*
- **Git**

### Environment Configuration

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/sandil2003/MOODZ.git
   cd MOODZ
   ```

2. **Configure Backend Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     copy "backend\.env.example" "backend\.env"
     ```
   - **Linux / macOS**:
     ```bash
     cp backend/.env.example backend/.env
     ```

3. **Populate `backend/.env`**:
   ```env
   # Application Settings
   APP_NAME="MOODZ AI Agent"
   API_VERSION=1.0.0
   DEBUG=true

   # Databases
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/moodz_db
   REDIS_URL=redis://localhost:6379/0

   # AgentOps Observability
   PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317

   # AI Provider Keys
   OPENAI_API_KEY=your-openai-api-key
   GEMINI_API_KEY=your-gemini-api-key
   PINECONE_API_KEY=your-pinecone-api-key
   PINECONE_ENVIRONMENT=us-east-1
   PINECONE_INDEX_NAME=moodz-embeddings

   # Security & CORS
   SECRET_KEY=your-generated-jwt-secret-key
   CORS_ORIGINS=["http://localhost:4200","http://127.0.0.1:4200"]
   ```

---

### Running with Docker (Recommended)

Docker handles backend dependencies, PostgreSQL, Redis, Arize Phoenix, and Angular automatically.

#### 1. Development Mode (Live Hot-Reloading + AgentOps)
```bash
docker-compose -f docker-compose.dev.yml up --build
```
- **Frontend**: [http://localhost:4200](http://localhost:4200)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Arize Phoenix AgentOps UI**: [http://localhost:6006](http://localhost:6006)

#### 2. Production / Detached Mode
```bash
docker-compose up --build -d
```
To view logs:
```bash
docker-compose logs -f
```
To stop all services:
```bash
docker-compose down
```

---

### Running Locally (Without Docker)

#### Step 1: Start PostgreSQL, Redis & Phoenix
```bash
docker-compose up -d postgres redis phoenix
```

#### Step 2: Start the FastAPI Backend
```powershell
cd backend

# Activate virtual environment
# Windows (PowerShell):
..\moodz\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
uvicorn main:app --reload --port 8000
```

#### Step 3: Start the Angular Frontend
In a separate terminal:
```powershell
cd moodz-frontend
npm install
npm start
```
*Frontend runs at [http://localhost:4200](http://localhost:4200).*

---

### Running Google ADK Agent UI

To test the Mood Agent directly via the Google ADK web interface:

```powershell
cd backend
adk web app/agents/mood_agent
```
*Note: Always run `adk` from inside the `backend/` directory so Python correctly resolves the `app` package.*

---

## 📁 Project Structure

```
MOODZ/
├── backend/                            # FastAPI Backend & AI Orchestration
│   ├── app/
│   │   ├── agents/                     # Google ADK agent framework
│   │   │   ├── mood_agent/             # ADK root agent declaration
│   │   │   │   ├── __init__.py
│   │   │   │   └── agent.py            # root_agent declaration
│   │   │   └── mood_adk.py             # Traced ADK tools & agent specification
│   │   ├── core/                       # Core configurations, telemetry & privacy
│   │   │   ├── config.py               # Pydantic environment settings
│   │   │   ├── database.py             # Async SQLAlchemy session factory
│   │   │   ├── redis_client.py         # Async Redis client
│   │   │   ├── auth_utils.py           # JWT hashing & auth dependencies
│   │   │   ├── pii_scrubber.py         # [AgentOps] Sub-ms recursive PII redaction
│   │   │   └── telemetry.py            # [AgentOps] OpenTelemetry & Phoenix integration
│   │   ├── routes/                     # REST & WebSocket endpoints
│   │   │   ├── auth.py                 # Registration & JWT login
│   │   │   ├── chat.py                 # SSE chat streaming & feedback endpoints
│   │   │   ├── history.py              # PostgreSQL chat & Redis session history
│   │   │   ├── mood.py                 # Mood logs, trends, & statistics
│   │   │   └── health.py               # Liveness, DB, & Redis health checks
│   │   ├── services/                   # Business logic & AI pipelines
│   │   │   ├── mood_graph.py           # Traced LangGraph StateGraph hybrid orchestrator
│   │   │   ├── mood_agent.py           # Backward-compatible agent chain wrapper
│   │   │   ├── crisis_detector.py      # Hardened deterministic crisis & safety gate
│   │   │   ├── vector_service.py       # Pinecone semantic embeddings
│   │   │   ├── session_manager.py      # Redis short-term session buffering
│   │   │   └── custom_model.py         # Fine-tuned & local LLM integration
│   │   ├── utils/                      # Chat logging & helper routines
│   │   ├── models.py                   # SQLAlchemy database schemas
│   │   └── schemas.py                  # Pydantic validation & feedback schemas
│   ├── alembic/                        # Database migration scripts
│   ├── tasks/                          # Celery asynchronous worker tasks
│   ├── test/                           # Automated pytest suite & benchmarks
│   │   ├── evals/                      # [AgentOps] Automated evaluation test suites
│   │   │   ├── conftest.py             # Pytest path configurations
│   │   │   ├── test_crisis_benchmark.py# 100% Crisis Detection Recall benchmark
│   │   │   ├── test_empathy_evals.py   # DeepEval LLM-as-a-Judge empathy suite
│   │   │   ├── test_pii_scrubber.py    # PII sanitization validation tests
│   │   │   └── test_telemetry_export.py# OTel span generation tests
│   │   ├── test_split_routes.py        # Route integrity tests
│   │   └── test_crisis_detection.py    # Unit crisis gate tests
│   ├── main.py                         # FastAPI ASGI entry point (telemetry enabled)
│   ├── requirements.txt                # Python dependencies (OTel, Phoenix, DeepEval)
│   ├── Dockerfile                      # Production Docker container
│   ├── Dockerfile.dev                  # Development container
│   ├── CUSTOM_MODEL_GUIDE.md           # Guide for fine-tuned LLMs
│   └── LM_STUDIO_GUIDE.md              # Local inference guide (LM Studio)
│
├── moodz-frontend/                     # Angular 21 Single Page Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/                  # Page route components
│   │   │   │   ├── new-home/           # Landing page with agent cards
│   │   │   │   ├── mood-agent/         # Interactive mood chat interface
│   │   │   │   ├── mood-dashboard/     # Visual mood analytics & charts
│   │   │   │   ├── mood-history/       # Chat session inspection & logs
│   │   │   │   ├── journal-agent/      # Journal interface (preview)
│   │   │   │   └── study-agent/        # Study companion (preview)
│   │   │   ├── shared/                 # Shared navbar, modals, cards
│   │   │   ├── services/               # ThemeService, API & SSE services
│   │   │   └── styles/                 # TailwindCSS & dark mode styles
│   │   ├── public/                     # Static assets & favicon
│   │   ├── package.json                # Node dependencies & scripts
│   │   ├── angular.json                # Angular CLI configuration
│   │   └── Dockerfile & Dockerfile.dev # Frontend container specifications
│
├── .github/
│   └── workflows/
│       └── ci.yml                      # CI/CD with AgentOps crisis & empathy gates
├── docs/
│   └── azure_deployment_plan.md        # Comprehensive Azure Cloud Deployment Plan
├── docker-compose.yml                  # Production orchestration (with Phoenix)
├── docker-compose.dev.yml              # Development live-reload (with Phoenix)
└── README.md
```

---

## 🤖 AI Agents & Hybrid Orchestration

### Mood Agent (Active)

The Mood Agent acts as an empathetic emotional companion. Rather than relying on a monolithic prompt, it operates as a multi-step hybrid graph:

#### Google ADK Tool Bindings
Declarative agent tools in `backend/app/agents/mood_adk.py`, instrumented with OpenTelemetry:
- `check_crisis_tool`: Deterministic crisis evaluator.
- `retrieve_user_context_tool`: Concurrent multi-tier retrieval aggregating Redis short-term history, Pinecone semantic embeddings, and PostgreSQL profile facts.
- `persist_user_facts_tool`: Persists newly extracted personal facts into PostgreSQL and Pinecone.
- `persist_mood_entry_tool`: Records sentiment ratings and numerical mood scores (1–10).

#### LangGraph StateGraph Engine
Implemented in `backend/app/services/mood_graph.py`:
- **Deterministic Safety Gate Node (0ms, 0 tokens)**: Checks for emergency signals before invoking LLMs. If detected, short-circuits directly to crisis intervention.
- **Context Ingestion Node**: Concurrently fetches multi-tier memory via `asyncio.gather`.
- **Empathetic Companion Stream Node**: Streams pure Markdown tokens directly to the user with Time-to-First-Token (TTFT) instrumentation.
- **Asynchronous Background Profiler**: Non-blocking sub-agent analyzing the turn to extract durable user facts and numerical mood ratings without delaying the user stream.

#### Fine-Tuned & Local Model Support
Supports self-hosted open-source models (e.g., Qwen-2.5, Llama-3) via LM Studio or Google Colab endpoints. See [backend/CUSTOM_MODEL_GUIDE.md](backend/CUSTOM_MODEL_GUIDE.md) and [backend/LM_STUDIO_GUIDE.md](backend/LM_STUDIO_GUIDE.md).

---

## 🧪 Continuous Evaluation & Safety Gates

MOODZ enforces a **Zero-Fail Safety Policy** on mental health crisis detection and continuous quantitative evaluation of companion responses.

### 1. 100% Crisis Detection Recall Benchmark
Mental health companions cannot tolerate false negatives. The test suite in `backend/test/evals/test_crisis_benchmark.py` validates:
- **40+ Direct & Morphological Crisis Triggers**: Suicidal ideation, self-harm, hopelessness.
- **15+ Benign Control Statements**: Ensuring safe everyday conversational language (*"I'm killing time waiting for the bus"*) is never wrongly blocked.
- **Latency SLA**: Confirms safety gate execution in $<10\text{ms}$.
- **Constraint**: **100% Recall ($\text{False Negatives} = 0$)**.

Run the crisis safety gate:
```powershell
pytest backend/test/evals/test_crisis_benchmark.py -v
```

### 2. DeepEval LLM-as-a-Judge Empathy Suite
In `backend/test/evals/test_empathy_evals.py`:
- **Empathy & Emotional Validation**: Evaluates whether the companion validates user emotions before offering guidance (requires score $\ge 4/5$ or $0.85$).
- **Non-Clinical Safety Heuristics**: Automatically flags and fails any response making clinical diagnoses (*"I diagnose you with..."*) or prescribing medications.
- **Formatting Integrity**: Guarantees no raw JSON or metadata fences leak into conversational bubbles.

### 3. Automated CI/CD Quality Gates
Defined in `.github/workflows/ci.yml`:
On every pull request and push to `main`:
1. Runs ruff linter and route unit tests.
2. Executes the **Crisis Detection Benchmark Gate**. A single false negative blocks the PR automatically.
3. Runs the **DeepEval Empathy & Telemetry Gate**.

Run all AgentOps evals locally:
```powershell
pytest backend/test/evals -v
```

---

## ☁️ Azure Deployment Plan

MOODZ is designed for cloud-native deployment on **Microsoft Azure**, providing elastic scalability, automated SSL, zero-downtime deployments, and managed database isolation.

For the comprehensive deployment specification, see **[📄 Azure Deployment Plan](docs/azure_deployment_plan.md)**.

### Target Azure Infrastructure

| Component | Target Azure Service | Rationale |
|-----------|----------------------|-----------|
| **Frontend & Backend Compute** | **Azure Container Apps (ACA)** | Serverless microservices hosting with automatic horizontal scaling (including scale-to-zero) and built-in ingress. |
| **AgentOps Observability** | **Azure Container Apps / Managed VM** | Containerized Arize Phoenix instance storing traces, spans, and token spend. |
| **Relational Database** | **Azure Database for PostgreSQL (Flexible Server)** | Fully managed PostgreSQL with automated daily backups, VNet integration, and high availability. |
| **Cache & Sessions** | **Azure Cache for Redis** | Low-latency in-memory cache for session state and prompt caching. |
| **Container Registry** | **Azure Container Registry (ACR)** | Secure private Docker image repository with direct ACA continuous deployment triggers. |
| **Secrets & Keys** | **Azure Key Vault** | Enterprise encryption and secret rotation for API keys (`OPENAI_API_KEY`, `PINECONE_API_KEY`, DB credentials). |
| **CI/CD** | **GitHub Actions** | Automated build, test, crisis benchmark verification, and rollout on merge to `main`. |

---

## 📡 API Documentation

When the backend is running, explore interactive OpenAPI documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Primary API Endpoints

| Category | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| **Chat** | `POST` | `/api/moods/chat/stream` | Real-time SSE streaming chat with LangGraph hybrid orchestrator |
| **Chat** | `POST` | `/api/moods/chat/` | Standard non-streaming chat completion |
| **Chat** | `POST` | `/api/moods/chat/feedback` | **[AgentOps]** Record user feedback rating ($\pm 1$), comments & corrected mood |
| **Chat** | `WS` | `/api/moods/chat/ws/status/{session_id}` | WebSocket channel for real-time thought/status updates |
| **Mood** | `GET` | `/api/mood-data/mood-history/{user_id}` | Fetch historical mood logs and analytics |
| **Mood** | `POST` | `/api/mood-data/` | Manually log a mood check-in |
| **History** | `GET` | `/api/chat-history/sessions` | Retrieve past conversation sessions for a user |
| **History** | `GET` | `/api/chat-history/sessions/{session_id}` | Fetch full message transcripts for a session |
| **Auth** | `POST` | `/api/auth/register` | Register a new user account |
| **Auth** | `POST` | `/api/auth/login` | Authenticate and obtain JWT bearer token |
| **Health** | `GET` | `/health` | Application status & service readiness |
| **Health** | `GET` | `/health/db` | PostgreSQL connectivity health check |
| **Health** | `GET` | `/health/redis` | Redis connectivity health check |

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
