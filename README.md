# MOODZ 

<div align="center">
  <img src="moodz-frontend/public/favicon.ico" width="200" />
  
  **Your Personal AI Wellness Companion**
  
  An intelligent mental health platform powered by AI agents to support your emotional well-being, journaling, and learning journey.

  [![Angular](https://img.shields.io/badge/Angular-21.0-DD0031?logo=angular)](https://angular.io/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript)](https://www.typescriptlang.org/)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
</div>

---

## Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [AI Agents](#-ai-agents)
- [Development](#-development)
- [API Documentation](#-api-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

**MOODZ** is a comprehensive mental wellness platform that combines cutting-edge AI technology with thoughtful UX design to provide personalized emotional support, journaling assistance, and study guidance. The platform features three specialized AI agents, each designed to help users in different aspects of their personal development journey.


### 🎭 Mood Agent
- **Emotional Support**: Empathetic AI companion for mental health conversations
- **Mood Tracking**: Log and monitor your emotional states
- **Sentiment Analysis**: AI-powered analysis of your mood patterns
- **Crisis Detection**: Identifies concerning patterns and provides resources
- **Chat History**: Access past conversations and insights
- **Mood Dashboard**: Visualize your emotional journey with charts and analytics

### 📝 Journal Agent *(Coming Soon)*
- **Reflective Writing**: AI-assisted journaling for personal growth
- **Thought Organization**: Structure your ideas and reflections
- **Daily Prompts**: Guided journaling with thoughtful questions
- **Pattern Recognition**: Identify recurring themes in your entries

### 📚 Study Agent *(Coming Soon)*
- **Learning Assistant**: AI-powered study companion
- **Research Support**: Help with academic research and analysis
- **Custom Learning Plans**: Personalized study schedules
- **Topic Analysis**: Break down complex subjects into digestible parts


## Architecture

MOODZ follows a modern **microservices architecture** with separate frontend and backend services:

```
┌─────────────────────────────────────────────────────────┐
│                    MOODZ Platform                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐      │
│  │   Angular 21     │ ◄─────► │   FastAPI        │      │
│  │   Frontend       │  HTTP   │   Backend        │      │
│  │  (Port 4200)     │         │  (Port 8000)     │      │
│  └──────────────────┘         └──────────────────┘      │
│         │                              │                │
│         │                              ▼                │
│         │                     ┌─────────────────┐       │
│         │                     │   PostgreSQL    │       │
│         │                     │   Database      │       │
│         │                     └─────────────────┘       │
│         │                              │                │
│         │                              ▼                |
│         |                     ┌─────────────────┐       |
│         │                     │   Pinecone      │       │
│         │                     │   Database      │       │
│         │                     └─────────────────┘       │
│         │                              │                │
│         │                              ▼                │
│         │                     ┌─────────────────┐       │
│         │                     │     Redis       │       │
│         │                     │     Cache       │       │
│         │                     └─────────────────┘       │
│         │                              │                │
│         │                              ▼                │
│         │                     ┌─────────────────┐       │
│         └────────────────────►│   AI Services   │       │
│                               │  OpenAI/Gemini  │       │
│                               │    Pinecone     │       │
│                               └─────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Components

1. **Frontend (Angular 21)**
   - Standalone components architecture
   - Signal-based state management
   - Reactive forms and routing
   - Markdown rendering for AI responses

2. **Backend (FastAPI)**
   - Async/await for high performance
   - RESTful API with streaming support
   - Database ORM with SQLAlchemy
   - Redis caching layer

3. **AI Services**
   - OpenAI GPT models for conversation
   - Google Gemini for advanced reasoning
   - Pinecone for vector embeddings
   - LangChain for agent orchestration

4. **Data Layer**
   - PostgreSQL for persistent storage
   - Redis for session management
   - Alembic for database migrations

---

## Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Angular** | 21.0 | Frontend framework |
| **TypeScript** | 5.9 | Type-safe JavaScript |
| **TailwindCSS** | 4.1 | Utility-first CSS |
| **RxJS** | 7.8 | Reactive programming |
| **ngx-markdown** | 21.0 | Markdown rendering |
| **Signals** | Built-in | State management |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | Latest | Web framework |
| **Python** | 3.11+ | Programming language |
| **SQLAlchemy** | Latest | ORM |
| **Alembic** | Latest | Database migrations |
| **Pydantic** | Latest | Data validation |
| **Uvicorn** | Latest | ASGI server |

### AI & ML
| Service | Purpose |
|---------|---------|
| **OpenAI** | GPT models for conversation |
| **Google Gemini** | Advanced AI reasoning |
| **Pinecone** | Vector database for embeddings |
| **LangChain** | Agent orchestration framework |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **PostgreSQL** | Primary database |
| **Redis** | Caching and sessions |
| **Docker** | Containerization |
| **Celery** | Background task processing |

---

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **Docker** and Docker Compose (optional)
- **Git**

### Environment Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/MOODZ.git
   cd MOODZ
   ```

2. **Set Up Backend**
   ```bash
   cd "MOOD AI AGENT"
   
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure environment
   copy .env.example .env
   # Edit .env with your API keys
   ```

3. **Set Up Frontend**
   ```bash
   cd moodz-frontend
   
   # Install dependencies
   npm install
   ```

### Running with Docker (Recommended)

```bash
cd "MOOD AI AGENT"
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- FastAPI backend on port 8000

Then start the frontend:
```bash
cd moodz-frontend
npm start
```

Access the application at **http://localhost:4200**

### Running Locally (Without Docker)

1. **Start Backend Services**
   ```bash
   # Start PostgreSQL and Redis manually or via Docker
   docker-compose up -d postgres redis
   
   # Run FastAPI
   cd "MOOD AI AGENT"
   uvicorn main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd moodz-frontend
   ng serve
   ```

### Environment Variables

Create a `.env` file in the `MOOD AI AGENT` directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4

# Google Gemini Configuration
GOOGLE_API_KEY=your-google-api-key

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=mood-index

# Database Configuration
POSTGRES_USER=moodz_user
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=moodz_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 📁 Project Structure

```
MOODZ/
├── moodz-frontend/              # Angular frontend application
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/           # Page components
│   │   │   │   ├── new-home/    # Landing page with agent cards
│   │   │   │   ├── mood-agent/  # Mood chat interface
│   │   │   │   ├── mood-dashboard/ # Analytics dashboard
│   │   │   │   ├── mood-history/   # Chat history
│   │   │   │   ├── journal-agent/  # Journal interface (coming soon)
│   │   │   │   └── study-agent/    # Study interface (coming soon)
│   │   │   ├── shared/          # Shared components
│   │   │   │   └── navbar/      # Navigation bar
│   │   │   ├── services/        # Angular services
│   │   │   │   └── theme.service.ts  # Dark mode management
│   │   │   └── styles/          # Global styles
│   │   │       └── dark-mode.css     # Dark mode styles
│   │   └── styles.css           # Global CSS
│   ├── public/                  # Static assets
│   ├── angular.json             # Angular configuration
│   ├── tailwind.config.js       # Tailwind configuration
│   └── package.json             # Frontend dependencies
│
├── MOOD AI AGENT/               # FastAPI backend
│   ├── app/
│   │   ├── routes/              # API endpoints
│   │   │   ├── chat.py          # Chat streaming
│   │   │   ├── mood_data.py     # Mood tracking
│   │   │   ├── chat_history.py  # Chat history
│   │   │   └── health.py        # Health checks
│   │   ├── services/            # Business logic
│   │   │   ├── mood_chain.py    # AI agent chain
│   │   │   ├── vector_service.py # Pinecone integration
│   │   │   └── crisis_detection.py # Crisis detection
│   │   ├── models/              # Database models
│   │   ├── database.py          # Database setup
│   │   └── redis_client.py      # Redis client
│   ├── alembic/                 # Database migrations
│   ├── celery/                  # Background tasks
│   ├── config.py                # Configuration
│   ├── main.py                  # FastAPI app
│   ├── requirements.txt         # Python dependencies
│   ├── docker-compose.yml       # Docker services
│   └── Dockerfile               # Docker image
│
├── JOURNAL AI AGENT/            # Journal agent (coming soon)
├── STUDY AI AGENT/              # Study agent (coming soon)
└── README.md                    # This file
```

---

## AI Agents

### Mood Agent (Active)

The Mood Agent is your empathetic AI companion for emotional support and mental wellness.

**Features:**
- Real-time streaming chat responses
- Context-aware conversations using chat history
- Sentiment analysis and mood tracking
- Crisis detection with resource recommendations
- Mood score calculation (1-10 scale)
- Visual mood dashboard with charts
- Chat history management

**Technology:**
- LangChain agent framework
- OpenAI GPT-4 for conversation
- Pinecone for semantic memory
- PostgreSQL for chat persistence
- Redis for session caching

**API Endpoints:**
- `POST /api/chat/stream` - Stream chat responses
- `GET /api/mood-data/` - Get mood entries
- `POST /api/mood-data/` - Create mood entry
- `GET /api/chat-history/` - Get chat sessions
- `DELETE /api/chat-history/{session_id}` - Delete session

### Journal Agent (Coming Soon)

AI-powered journaling assistant for personal reflection and growth.

### Study Agent (Coming Soon)

Intelligent study companion for academic success.

---

## Development

### Frontend Development

```bash
cd moodz-frontend

# Start dev server
npm start

# Build for production
npm run build

# Run tests
npm test

# Lint code
ng lint
```

### Backend Development

```bash
cd "MOOD AI AGENT"

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run with auto-reload
uvicorn main:app --reload

# Run tests
pytest

# Create database migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Code Style

**Frontend:**
- Follow Angular style guide
- Use standalone components
- Prefer signals over observables for state
- Use `input()` and `output()` functions
- Set `ChangeDetectionStrategy.OnPush`

**Backend:**
- Follow PEP 8 style guide
- Use type hints
- Write async functions where possible
- Document with docstrings

### Dark Mode Implementation

The application supports system-wide dark mode:

1. **ThemeService** manages dark mode state
2. CSS variables for theming
3. `:host-context(.dark)` selectors
4. Smooth transitions (300ms)

Toggle dark mode via the navbar icon.

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Chat
```http
POST /api/chat/stream
Content-Type: application/json

{
  "message": "I'm feeling anxious today",
  "session_id": "uuid-here"
}
```

#### Mood Data
```http
GET /api/mood-data/?user_id=1&limit=10
POST /api/mood-data/
{
  "user_id": 1,
  "mood_score": 7,
  "sentiment": "positive",
  "message": "Feeling great!"
}
```

