# MOOD AI Agent

AI-powered mood analysis and recommendation system built with FastAPI, PostgreSQL, Redis, OpenAI, and Pinecone.

## 🚀 Features

- **FastAPI Framework**: High-performance async web framework
- **PostgreSQL Database**: Robust relational database with async support
- **Redis Caching**: Fast in-memory caching for improved performance
- **OpenAI Integration**: AI-powered natural language processing
- **Pinecone Vector DB**: Semantic search and embeddings storage
- **Docker Compose**: Easy local development environment
- **Health Monitoring**: Built-in health check endpoints

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- Pinecone API key

## 🛠️ Installation

### 1. Clone the Repository

```bash
cd "c:\Users\sandi\Documents\AI\MOODZ\MOOD AI AGENT"
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update with your credentials:

```bash
copy .env.example .env
```

Edit `.env` and add your API keys:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment-here
```

## 🐳 Docker Compose Setup

### Start All Services

```bash
docker-compose up -d
```

This will start:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **FastAPI** on port 8000

### Check Service Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f fastapi
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Stop Services

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

## 🏃 Running Locally (Without Docker)

If you prefer to run the application without Docker:

### 1. Start PostgreSQL and Redis

Make sure PostgreSQL and Redis are running locally, or start only those services with Docker:

```bash
docker-compose up -d postgres redis
```

### 2. Update .env File

Update the `.env` file to use localhost:

```env
POSTGRES_HOST=localhost
REDIS_HOST=localhost
```

### 3. Run the Application

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## 📚 API Documentation

Once the application is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Info**: http://localhost:8000/api/info

## 🔍 Health Checks

The application provides health check endpoints:

- **General Health**: `GET /health/`
- **Database Health**: `GET /health/db`
- **Redis Health**: `GET /health/redis`

Example:

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/health/db
curl http://localhost:8000/health/redis
```

## 📁 Project Structure

```
MOOD AI AGENT/
├── app/
│   ├── __init__.py
│   ├── database.py          # Database configuration
│   ├── redis_client.py      # Redis client setup
│   ├── models/              # SQLAlchemy models
│   │   └── __init__.py
│   └── routes/              # API routes
│       ├── __init__.py
│       └── health.py        # Health check endpoints
├── config.py                # Application configuration
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Docker image definition
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🔧 Configuration

All configuration is managed through environment variables defined in `.env`:

### Application Settings
- `APP_NAME`: Application name
- `DEBUG`: Debug mode (True/False)
- `API_VERSION`: API version

### Database Settings
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: Database name
- `POSTGRES_HOST`: Database host
- `POSTGRES_PORT`: Database port

### Redis Settings
- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port
- `REDIS_DB`: Redis database number

### AI Services
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model to use
- `PINECONE_API_KEY`: Pinecone API key
- `PINECONE_ENVIRONMENT`: Pinecone environment
- `PINECONE_INDEX_NAME`: Pinecone index name

### Security
- `SECRET_KEY`: Secret key for JWT tokens
- `ALGORITHM`: JWT algorithm
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

## 🧪 Development

### Adding New Routes

1. Create a new file in `app/routes/`
2. Define your router:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/your-route", tags=["Your Tag"])

@router.get("/")
async def your_endpoint():
    return {"message": "Hello"}
```

3. Include the router in `main.py`:

```python
from app.routes import your_route
app.include_router(your_route.router)
```

### Adding Database Models

1. Create a new file in `app/models/`
2. Define your model:

```python
from sqlalchemy import Column, Integer, String
from app.database import Base

class YourModel(Base):
    __tablename__ = "your_table"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
```

3. Import the model in `app/models/__init__.py`

## 🐛 Troubleshooting

### Port Already in Use

If ports 5432, 6379, or 8000 are already in use, you can change them in `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Change host port
```

### Database Connection Issues

Check if PostgreSQL is running:

```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Redis Connection Issues

Check if Redis is running:

```bash
docker-compose ps redis
docker-compose logs redis
```

## 📝 License

This project is private and proprietary.

## 🤝 Contributing

This is a private project. Contact the maintainer for contribution guidelines.

## 📧 Contact

For questions or support, please contact the project maintainer.
