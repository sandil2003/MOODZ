# MOODZ 

<div align="center">
  <img src="moodz-frontend/public/favicon.ico" width="180" alt="MOODZ Logo" />
  
  # Your Personal AI Wellness Companion
  
  An intelligent mental health platform powered by modern multi-agent AI architectures to support your emotional well-being, reflective journaling, and personalized growth.

  [![Angular](https://img.shields.io/badge/Angular-21.0-DD0031?logo=angular)](https://angular.io/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-blueviolet)](https://github.com/langchain-ai/langgraph)
  [![Google ADK](https://img.shields.io/badge/Google_ADK-2.13+-4285F4?logo=google)](https://github.com/google/adk)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript)](https://www.typescriptlang.org/)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
  [![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4.1-38B2AC?logo=tailwindcss)](https://tailwindcss.com/)
  [![Azure](https://img.shields.io/badge/Azure-Cloud_Native-0078D4?logo=microsoftazure)](https://azure.microsoft.com/)
</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
  - [System Architecture Diagram](#system-architecture-diagram)
  - [Multi-Agent & StateGraph Flow](#multi-agent--stategraph-flow)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Running with Docker (Recommended)](#running-with-docker-recommended)
  - [Running Locally](#running-locally-without-docker)
  - [Running Google ADK Agent UI](#running-google-adk-agent-ui)
- [Project Structure](#-project-structure)
- [AI Agents & Hybrid Orchestration](#-ai-agents--hybrid-orchestration)
  - [Mood Agent (Active)](#mood-agent-active)
  - [Google ADK Integration](#google-adk-integration)
  - [LangGraph StateGraph Engine](#langgraph-stategraph-engine)
  - [Fine-Tuned & Local Model Support](#fine-tuned--local-model-support)
- [☁️ Azure Deployment Plan](#️-azure-deployment-plan)
- [Development & Testing](#-development--testing)
- [API Documentation](#-api-documentation)
- [License](#-license)

---

## 🌟 Overview

**MOODZ** is a state-of-the-art mental wellness platform that bridges cutting-edge generative AI with compassionate, thoughtful human experience design. Designed to provide empathetic conversational support, mood journaling, and cognitive insights, MOODZ leverages a **hybrid multi-agent architecture** combining **Google ADK** (Agent Development Kit) for multi-agent capabilities and **LangGraph StateGraph** for deterministic, zero-latency safety gating and multi-tier contextual memory.

### Active & Upcoming Agents
- **Mood Agent (Active)**: Empathetic AI companion with real-time SSE streaming, safety gates, sentiment analysis, and episodic vector memory.
- **Journal Agent (In Development)**: Reflective thought-structuring and guided journaling with daily prompts.
- **Study Agent (In Development)**: Adaptive learning assistant for cognitive breakdown and study scheduling.

---

## ✨ Key Features

- **🛡️ Deterministic Zero-Latency Safety Gate**: Instantly flags crisis/self-harm signals with 0 token overhead and 0ms LLM latency, immediately routing to crisis resources (988 Lifeline).
- **🧠 Multi-Tier Context Memory**:
  - *Short-Term Memory*: In-memory conversation state backed by Redis.
  - *Long-Term Episodic Memory*: Semantic vector embeddings stored in Pinecone with cosine similarity search.
  - *User Fact Profile*: Persistent relational user insights and preferences stored in PostgreSQL.
- **⚡ Real-Time Streaming & WebSockets**: Server-Sent Events (SSE) for low-latency token streaming, supplemented by WebSocket live status channels.
- **🤖 Multi-Model & Custom LLM Flexibility**: Supports OpenAI GPT-4, Google Gemini Flash/Pro, and custom fine-tuned models (e.g., Qwen via LM Studio / Colab endpoints).
- **📊 Interactive Analytics Dashboard**: Track emotional trends over time, sentiment distribution, and conversation history.
- **🌓 Modern Glassmorphic UI**: Angular 21 with Signals, TailwindCSS v4, dark mode support, and full Markdown rendering.

---

## 🏛️ Architecture

MOODZ adopts a modern, asynchronous microservices architecture designed for modularity, resilience, and real-time responsiveness.

### System Architecture Diagram

```mermaid
graph TB
    %% Client Tier
    subgraph ClientTier ["Client Tier (Frontend)"]
        direction TB
        Browser["User Browser"]
        AngularApp["Angular 21 SPA<br/>(Signals & Components)"]
        Tailwind["TailwindCSS v4.1<br/>(Glassmorphic Dark UI)"]
        
        Browser <--> AngularApp
        AngularApp --- Tailwind
    end

    %% Application Tier
    subgraph AppTier ["Application Tier (Backend)"]
        direction TB
        FastAPI["FastAPI Web Framework<br/>(Async ASGI / Uvicorn)"]
        Router["Router Layer<br/>(Auth, Chat, Mood, History)"]
        
        subgraph Orchestration ["Agent & Hybrid Orchestrator"]
            ADK["Google ADK Agent<br/>(Declarative Tools)"]
            LangGraph["LangGraph StateGraph<br/>(Safety Gate, Routing, Memory)"]
        end
        
        FastAPI --> Router
        Router --> Orchestration
    end

    %% Data Tier
    subgraph DataTier ["Data & Caching Tier"]
        direction LR
        Postgres[("PostgreSQL DB<br/>(Relational Users, History, Facts)")]
        RedisClient[("Redis Cache<br/>(Sessions & Short-Term Memory)")]
    end

    %% External & Custom AI Tier
    subgraph AITier ["AI & Vector Tier"]
        direction LR
        Pinecone[("Pinecone Vector DB<br/>(Semantic Embeddings)")]
        OpenAI["OpenAI GPT Models"]
        Gemini["Google Gemini Models"]
        CustomLLM["Custom Fine-Tuned LLM<br/>(LM Studio / Colab)"]
    end

    %% Connections
    AngularApp == "HTTP REST / SSE Stream / WS" ==> FastAPI
    Orchestration == "SQLAlchemy (Async)" ==> Postgres
    Orchestration == "Key-Value State" ==> RedisClient
    Orchestration == "RAG Semantic Search" ==> Pinecone
    Orchestration == "Inference" ==> OpenAI
    Orchestration == "Inference & Fallback" ==> Gemini
    Orchestration == "Local / Fine-Tuned" ==> CustomLLM

    %% Styles
    classDef client fill:#EBF3FC,stroke:#2B78E4,stroke-width:2px,color:#1A365D;
    classDef backend fill:#E8F8F5,stroke:#117A65,stroke-width:2px,color:#0B3C33;
    classDef data fill:#FEF9E7,stroke:#D35400,stroke-width:2px,color:#5E2F00;
    classDef ai fill:#F5EEF8,stroke:#7D3C98,stroke-width:2px,color:#4A148C;

    class Browser,AngularApp,Tailwind client;
    class FastAPI,Router,ADK,LangGraph backend;
    class Postgres,RedisClient data;
    class Pinecone,OpenAI,Gemini,CustomLLM ai;
```

### Multi-Agent & StateGraph Flow

```mermaid
flowchart TD
    UserMsg([User Message]) --> SafetyGate{Safety Gate<br/>Crisis Check?}
    SafetyGate -- "Immediate Risk (0ms / 0 tokens)" --> EmergencyResponse[Return Crisis Helpline Resources]
    SafetyGate -- "Safe" --> ContextRetrieval[Multi-Tier Retrieval<br/>Redis + Pinecone + Postgres]
    ContextRetrieval --> IntentRouting{Intent Router<br/>Emotional / Casual / Advice}
    IntentRouting --> GenerationNode[Empathetic LLM Generation<br/>OpenAI / Gemini / Custom LLM]
    GenerationNode --> StreamOut([SSE Token Streaming])
    GenerationNode --> PostProcessing[Post-Processing Node<br/>Mood Scoring + Fact Extraction]
    PostProcessing --> PersistDB[(Save to PostgreSQL & Pinecone)]
```

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Angular** | 21.0 | Signal-based reactive web application |
| **TypeScript** | 5.9 | Type-safe enterprise JavaScript |
| **TailwindCSS** | 4.1 | Utility-first styling with dark mode & animations |
| **RxJS** | 7.8 | Reactive asynchronous stream handling |
| **ngx-markdown** | 21.0 | Formatted markdown parsing in chat bubbles |

### Backend & AI Orchestration
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | Latest | High-concurrency async Python ASGI web framework |
| **Python** | 3.11+ | Core backend runtime (tested up to Python 3.14) |
| **LangGraph** | 0.2+ | StateGraph pipeline & conditional node orchestration |
| **Google ADK** | 2.13+ | Multi-agent coordination and standardized agent toolkits |
| **SQLAlchemy** | 2.0+ (Async) | Asynchronous ORM for relational persistence |
| **Alembic** | Latest | Automated database schema migrations |
| **Celery** | Latest | Background task queue & worker framework |
| **Pinecone** | Latest | Vector database for episodic long-term memory |
| **Redis** | 7+ | Session state store and real-time caching |
| **PostgreSQL** | 15+ | Relational database for accounts, sessions, and facts |

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
   Copy the example environment file inside `backend`:
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

Docker handles backend dependencies, PostgreSQL, Redis, and Angular automatically.

#### 1. Development Mode (Live Hot-Reloading)
Mounts local source code into containers for real-time frontend and backend reloading:
```bash
docker-compose -f docker-compose.dev.yml up --build
```
- **Frontend**: [http://localhost:4200](http://localhost:4200)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

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

#### Step 1: Start PostgreSQL & Redis
If you don't have local Postgres and Redis instances:
```bash
docker-compose up -d postgres redis
```

#### Step 2: Start the FastAPI Backend
```powershell
# Navigate into backend directory
cd backend

# Activate virtual environment
# Windows (PowerShell):
.\..\moodz\Scripts\Activate.ps1
# (or create a new venv: python -m venv venv && .\venv\Scripts\Activate.ps1)

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
uvicorn main:app --reload --port 8000
```

#### Step 3: Start the Angular Frontend
Open a separate terminal:
```powershell
cd moodz-frontend

# Install dependencies
npm install

# Start Angular development server
npm start
```
*Frontend runs at [http://localhost:4200](http://localhost:4200).*

---

### Running Google ADK Agent UI

To explore and test the Mood Agent directly via the Google ADK web interface:

```powershell
cd backend
adk web app/agents/mood_agent
```
*Note: Always run `adk` from inside the `backend/` directory so Python correctly resolves the `app` package.*

---

## 📁 Project Structure

```
MOODZ/
├── backend/                            # FastAPI & AI Engine
│   ├── app/
│   │   ├── agents/                     # Google ADK agent framework
│   │   │   ├── mood_agent/             # ADK root agent declaration
│   │   │   │   ├── __init__.py
│   │   │   │   └── agent.py            # root_agent declaration
│   │   │   └── mood_adk.py             # ADK tools & agent specification
│   │   ├── core/                       # Core configurations & clients
│   │   │   ├── config.py               # Pydantic environment settings
│   │   │   ├── database.py             # Async SQLAlchemy session factory
│   │   │   ├── redis_client.py         # Async Redis client
│   │   │   └── auth_utils.py           # JWT hashing & auth dependencies
│   │   ├── routes/                     # REST & WebSocket endpoints
│   │   │   ├── auth.py                 # Registration & JWT login
│   │   │   ├── chat.py                 # SSE chat streaming & WebSocket status
│   │   │   ├── history.py              # PostgreSQL chat & Redis session history
│   │   │   ├── mood.py                 # Mood logs, trends, & statistics
│   │   │   └── health.py               # Liveness, DB, & Redis health checks
│   │   ├── services/                   # Business logic & AI pipelines
│   │   │   ├── mood_graph.py           # LangGraph StateGraph hybrid orchestrator
│   │   │   ├── mood_agent.py           # Backward-compatible agent chain wrapper
│   │   │   ├── crisis_detector.py      # Deterministic crisis & safety gate
│   │   │   ├── vector_service.py       # Pinecone semantic embeddings
│   │   │   ├── session_manager.py      # Redis short-term session buffering
│   │   │   └── custom_model.py         # Fine-tuned & local LLM integration
│   │   ├── utils/                      # Chat logging & helper routines
│   │   ├── models.py                   # SQLAlchemy database schemas
│   │   └── schemas.py                  # Pydantic validation schemas
│   ├── alembic/                        # Database migration scripts
│   ├── tasks/                          # Celery asynchronous worker tasks
│   ├── test/                           # Automated pytest suite & benchmarks
│   ├── main.py                         # FastAPI ASGI entry point
│   ├── requirements.txt                # Python dependencies
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
│   ├── public/                         # Static assets & favicon
│   ├── package.json                    # Node dependencies & scripts
│   ├── angular.json                    # Angular CLI configuration
│   └── Dockerfile & Dockerfile.dev     # Frontend container specifications
│
├── docs/
│   └── azure_deployment_plan.md        # Comprehensive Azure Cloud Deployment Plan
├── docker-compose.yml                  # Production orchestration
├── docker-compose.dev.yml              # Development live-reload orchestration
└── README.md
```

---

## 🤖 AI Agents & Hybrid Orchestration

### Mood Agent (Active)

The Mood Agent acts as an empathetic emotional companion. Rather than relying on a monolithic prompt, it operates as a multi-step hybrid graph:

1. **Google ADK Agent Definition**:
   Declarative agent declaration in `backend/app/agents/mood_agent/agent.py` exposing four core tools:
   - `check_crisis_tool`: Fast safety classifier.
   - `retrieve_user_context_tool`: Multi-tier context aggregator (Redis + Pinecone + PostgreSQL).
   - `save_mood_entry_tool`: Persists detected mood score and sentiment.
   - `search_wellness_tips_tool`: DuckDuckGo free search for non-clinical wellness tips.

2. **LangGraph StateGraph Engine**:
   Implemented in `backend/app/services/mood_graph.py`, managing the state transition pipeline:
   - **Deterministic Crisis Node**: Evaluates input before invoking external LLMs. If self-harm or severe distress is detected, execution short-circuits with verified crisis helpline info.
   - **Context Retrieval Node**: Concurrent querying of active session messages from Redis, semantic embeddings from Pinecone, and user facts from PostgreSQL.
   - **Empathetic Generation Node**: Streams tokens via OpenAI, Gemini, or custom LLM with fallback capabilities.
   - **Post-Processing & Logging Node**: Asynchronously extracts user facts, computes mood sentiment (1-10 scale), and updates databases.

3. **Fine-Tuned & Local Model Support**:
   - Supports self-hosted open-source models (e.g., Qwen-2.5, Llama-3) via LM Studio or Google Colab endpoints.
   - For configuration details, see [backend/CUSTOM_MODEL_GUIDE.md](backend/CUSTOM_MODEL_GUIDE.md) and [backend/LM_STUDIO_GUIDE.md](backend/LM_STUDIO_GUIDE.md).

---

## ☁️ Azure Deployment Plan

MOODZ is designed for cloud-native deployment on **Microsoft Azure**, providing elastic scalability, automated SSL, zero-downtime deployments, and managed database isolation.

For the comprehensive deployment specification, see **[📄 Azure Deployment Plan](docs/azure_deployment_plan.md)**.

### Target Azure Infrastructure

| Component | Target Azure Service | Rationale |
|-----------|----------------------|-----------|
| **Frontend & Backend Compute** | **Azure Container Apps (ACA)** | Serverless microservices hosting with automatic horizontal scaling (including scale-to-zero) and built-in ingress. |
| **Relational Database** | **Azure Database for PostgreSQL (Flexible Server)** | Fully managed PostgreSQL with automated daily backups, VNet integration, and high availability. |
| **Cache & Sessions** | **Azure Cache for Redis** | Low-latency in-memory cache for session state and prompt caching. |
| **Container Registry** | **Azure Container Registry (ACR)** | Secure private Docker image repository with direct ACA continuous deployment triggers. |
| **Secrets & Keys** | **Azure Key Vault** | Enterprise encryption and secret rotation for API keys (`OPENAI_API_KEY`, `PINECONE_API_KEY`, DB credentials) with Managed Identity access. |
| **CI/CD** | **GitHub Actions** | Automated build, test, containerization, and rollout on merge to `main`. |

---

## 🧪 Development & Testing

### Running Backend Tests
Execute the full pytest suite (including ADK agent verification, split route tests, and crisis gate benchmarks):
```bash
cd backend
pytest
```

Run specific test suites:
```bash
# Test Google ADK and LangGraph hybrid agent
pytest test/test_adk_hybrid_agent.py -v

# Test route integrity
pytest test/test_split_routes.py -v

# Test deterministic safety gate
pytest test/test_crisis_detection.py -v
```

### Running Frontend Tests
```bash
cd moodz-frontend
npm test
```

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
