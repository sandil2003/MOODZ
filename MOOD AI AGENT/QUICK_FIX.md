# 🚨 Quick Fix: Database Migration Error

## The Problem

You're getting `password authentication failed for user "postgre"` because:
1. **Docker Desktop is NOT running** ❌
2. PostgreSQL database is not started

## The Solution

### Step 1: Start Docker Desktop

1. Open **Docker Desktop** application on Windows
2. Wait for it to fully start (you'll see the Docker icon in system tray turn green)
3. This may take 30-60 seconds

### Step 2: Verify Docker is Running

```powershell
docker --version
```

You should see output like: `Docker version 24.x.x`

### Step 3: Fix .env File (Important!)

The error shows username as `"postgre"` but it should be `"postgres"`.

**Option A: Use your current password**
Edit `.env` file and change:
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Candoany123
```

**Option B: Use default credentials**
Edit `.env` file:
```env
POSTGRES_USER=moodz_user
POSTGRES_PASSWORD=moodz_password
```

### Step 4: Start PostgreSQL

```powershell
# Start PostgreSQL and Redis
docker-compose up -d postgres redis
```

Wait 10-15 seconds for services to initialize.

### Step 5: Verify Services are Running

```powershell
docker-compose ps
```

You should see:
```
NAME              STATUS
moodz_postgres    Up (healthy)
moodz_redis       Up (healthy)
```

### Step 6: Run Migration

```powershell
alembic revision --autogenerate -m "Create users table"
alembic upgrade head
```

## Quick Commands Summary

```powershell
# 1. Start Docker Desktop (manually)

# 2. Start database services
docker-compose up -d postgres redis

# 3. Wait 15 seconds, then check status
docker-compose ps

# 4. Run migration
alembic revision --autogenerate -m "Create users table"
alembic upgrade head
```

## If Still Having Issues

### Reset Everything
```powershell
# Stop all services
docker-compose down -v

# Start fresh
docker-compose up -d postgres redis

# Wait 15 seconds
Start-Sleep -Seconds 15

# Try migration again
alembic revision --autogenerate -m "Create users table"
```

### Check PostgreSQL Logs
```powershell
docker-compose logs postgres
```

### Test Database Connection
```powershell
docker exec -it moodz_postgres psql -U postgres -d moodz_db
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Docker Desktop not running | Start Docker Desktop application |
| Port 5432 already in use | Stop other PostgreSQL instances or change port in docker-compose.yml |
| Username mismatch | Ensure `.env` has `POSTGRES_USER=postgres` (not `postgre`) |
| Password incorrect | Match password in `.env` with docker-compose.yml |

---

**Next Step:** Start Docker Desktop, then run the commands above! 🚀
