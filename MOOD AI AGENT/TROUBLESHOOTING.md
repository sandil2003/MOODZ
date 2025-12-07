# Quick Fix Guide for Alembic Migration Error

## Problem
The error `password authentication failed for user "postgre"` occurs because:
1. PostgreSQL is not running
2. There may be a username mismatch in the `.env` file

## Solution

### Step 1: Start PostgreSQL with Docker Compose

```bash
# Start PostgreSQL and Redis services
docker-compose up -d postgres redis
```

Wait for the services to start (about 10-15 seconds), then verify:

```bash
# Check if services are running
docker-compose ps
```

You should see both `postgres` and `redis` with status "Up".

### Step 2: Verify .env Configuration

Open your `.env` file and ensure the database credentials match:

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Candoany123
POSTGRES_DB=moodz_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

**Important:** The username should be `postgres` (full word), not `postgre`.

If you see `POSTGRES_USER=postgre`, change it to `POSTGRES_USER=postgres`.

### Step 3: Update docker-compose.yml (if needed)

Make sure `docker-compose.yml` has matching credentials:

```yaml
postgres:
  environment:
    POSTGRES_USER: ${POSTGRES_USER:-postgres}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-Candoany123}
    POSTGRES_DB: ${POSTGRES_DB:-moodz_db}
```

### Step 4: Restart PostgreSQL

```bash
# Stop and remove containers
docker-compose down

# Start fresh
docker-compose up -d postgres redis
```

### Step 5: Test Database Connection

```bash
# Test connection using psql (if installed)
docker exec -it moodz_postgres psql -U postgres -d moodz_db

# Or check logs
docker-compose logs postgres
```

### Step 6: Run Alembic Migration

Once PostgreSQL is running:

```bash
# Generate migration
alembic revision --autogenerate -m "Create users table"

# Apply migration
alembic upgrade head
```

## Alternative: Use Default Credentials

If you want to use the default credentials from the template, update your `.env`:

```env
POSTGRES_USER=moodz_user
POSTGRES_PASSWORD=moodz_password
POSTGRES_DB=moodz_db
```

Then restart Docker Compose:

```bash
docker-compose down -v  # -v removes volumes
docker-compose up -d postgres redis
```

## Troubleshooting

### Check PostgreSQL Logs
```bash
docker-compose logs postgres
```

### Check if Port 5432 is Available
```powershell
# Windows PowerShell
netstat -ano | findstr :5432
```

### Connect to PostgreSQL Container
```bash
docker exec -it moodz_postgres bash
psql -U postgres
```

### Reset Everything
```bash
# Stop all services and remove volumes
docker-compose down -v

# Start fresh
docker-compose up -d postgres redis

# Wait 10 seconds, then run migration
alembic revision --autogenerate -m "Create users table"
alembic upgrade head
```
