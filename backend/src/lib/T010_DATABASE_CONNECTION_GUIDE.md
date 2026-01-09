# T010: Neon DB Connection Utility - Implementation Guide

**Task ID**: T010
**Status**: Completed
**Date**: 2026-01-05
**File**: `/backend/src/lib/database.py`

---

## Overview

This implementation provides async SQLAlchemy session management for Neon DB (serverless PostgreSQL) with optimized connection pooling, FastAPI dependency injection, and comprehensive error handling.

---

## Key Features

### 1. Async SQLAlchemy 2.0+ Integration
- **AsyncEngine** with `asyncpg` driver for non-blocking database I/O
- **async_sessionmaker** for creating async sessions
- **SQLAlchemy 2.0 style** with `future=True` flag
- Full type hints for IDE support and type safety

### 2. Serverless-Optimized Connection Pooling

#### Production/Serverless Mode (Vercel, AWS Lambda)
```python
# NullPool - No connection pooling
# Creates new connection per request, closes after response
# Prevents connection exhaustion in ephemeral environments
poolclass = NullPool
```

#### Development Mode
```python
# AsyncAdaptedQueuePool - Connection pooling for better performance
pool_size = 5           # Persistent connections
max_overflow = 10       # Additional connections beyond pool_size
pool_timeout = 30       # Seconds to wait for connection
pool_recycle = 3600     # Recycle connections after 1 hour
pool_pre_ping = True    # Verify connection health before use
```

### 3. FastAPI Dependency Injection
```python
from src.lib.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
```

### 4. Automatic Transaction Management
- **Commit** on successful request completion
- **Rollback** on exceptions
- **Session cleanup** after request
- Comprehensive error logging

### 5. Health Check Integration
```python
@app.get("/health")
async def health_check():
    db_health = await db_health_check()
    return {
        "status": "healthy",
        "database": db_health,
    }
```

---

## Usage Guide

### Application Startup (main.py)

```python
from src.lib.database import init_db, close_db

@app.on_event("startup")
async def startup():
    """Initialize database connection pool"""
    init_db()

@app.on_event("shutdown")
async def shutdown():
    """Close database connections gracefully"""
    await close_db()
```

### FastAPI Endpoints

```python
from src.lib.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

@app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@app.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user
```

### Manual Transaction Control

```python
@app.post("/complex-operation")
async def complex_operation(
    db: AsyncSession = Depends(get_db)
):
    try:
        # Multiple operations in single transaction
        user = User(email="test@example.com")
        db.add(user)
        await db.flush()  # Get user.id without committing

        quiz = QuizResponse(user_id=user.id, quiz_data={...})
        db.add(quiz)

        # Explicit commit
        await db.commit()

        return {"user_id": user.id, "quiz_id": quiz.id}
    except Exception as e:
        # Rollback handled automatically by get_db()
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Environment Configuration

### Required Environment Variables

```bash
# .env file
NEON_DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Optional (for serverless environments)
SERVERLESS=true
ENV=production
```

### Database URL Formats

**Standard PostgreSQL**:
```
postgresql://user:password@host:port/database
```

**Neon DB (with SSL)**:
```
postgresql://user:password@ep-example-123.us-east-2.aws.neon.tech/dbname?sslmode=require
```

**Automatically converted to asyncpg**:
```
postgresql+asyncpg://user:password@host/database
```

---

## Connection Pool Settings Explanation

### NullPool (Production/Serverless)
**Why**: Serverless functions are stateless and ephemeral
- Each request creates a new connection
- Connection closed immediately after request
- Prevents connection leaks in serverless environments
- No persistent connections between requests

**Trade-offs**:
- Slower per-request (connection overhead)
- No connection limit issues
- Better for low-traffic, unpredictable workloads

### AsyncAdaptedQueuePool (Development)
**Why**: Better performance for long-running processes
- Reuses connections across requests
- Maintains pool of active connections
- Pre-ping ensures connection health

**Settings**:
- `pool_size=5`: Maximum persistent connections
- `max_overflow=10`: Additional connections under load (total 15)
- `pool_timeout=30`: Wait 30s for available connection
- `pool_recycle=3600`: Refresh connections every hour (prevents stale connections)
- `pool_pre_ping=True`: Test connection before use (detect failures)

**Trade-offs**:
- Faster per-request (connection reuse)
- Risk of exhausting connection pool under high load
- Better for high-traffic, predictable workloads

---

## Error Handling

### Common Errors and Solutions

#### 1. `NEON_DATABASE_URL not set`
```python
ValueError: NEON_DATABASE_URL environment variable is not set.
```
**Solution**: Add database URL to `.env` file

#### 2. `Database not initialized`
```python
RuntimeError: Database not initialized. Call init_db() during application startup.
```
**Solution**: Add `init_db()` to FastAPI startup event

#### 3. Connection Timeout
```python
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```
**Solution**: Increase `pool_size` or `max_overflow`, or switch to NullPool

#### 4. Connection Refused
```python
asyncpg.exceptions.ConnectionRefusedError
```
**Solution**:
- Verify database URL is correct
- Check network connectivity
- Ensure Neon DB project is active

---

## Testing

### Manual Testing (Health Check)

```bash
# Start FastAPI server
uvicorn main:app --reload

# Test health check endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "keto-meal-plan-api",
  "environment": "development",
  "components": {
    "api": "healthy",
    "database": {
      "status": "healthy",
      "database": "connected",
      "pool_size": 5,
      "pool_overflow": 0,
      "pool_checked_out": 0
    }
  }
}
```

### Unit Testing (Future - T029D)

```python
import pytest
from src.lib.database import get_db, init_db, close_db

@pytest.fixture
async def db_session():
    """Provide database session for tests"""
    init_db()
    async for session in get_db():
        yield session
    await close_db()

async def test_database_connection(db_session):
    """Test database connection"""
    result = await db_session.execute("SELECT 1")
    assert result.scalar() == 1
```

---

## Performance Considerations

### Connection Pool Sizing

**Formula**: `pool_size + max_overflow ≥ concurrent_requests`

**Examples**:
- Low traffic (1-5 concurrent): `pool_size=5, max_overflow=5`
- Medium traffic (10-20 concurrent): `pool_size=10, max_overflow=10`
- High traffic (50+ concurrent): Use NullPool or scale horizontally

### Query Optimization
- Use `selectinload()` for eager loading (prevent N+1 queries)
- Index foreign keys and frequently queried columns
- Use `EXPLAIN ANALYZE` for slow queries

### Monitoring
- Track connection pool utilization
- Monitor query execution time
- Set up alerts for pool exhaustion

---

## Migration to Alembic

### Using Database Engine in Migrations

```python
# alembic/env.py
from src.lib.database import get_database_url, Base

config.set_main_option("sqlalchemy.url", get_database_url())
target_metadata = Base.metadata
```

---

## Security Best Practices

1. **Never hardcode credentials** - Use environment variables
2. **Enable SSL/TLS** - Use `sslmode=require` in connection string
3. **Rotate credentials** - Update database passwords periodically
4. **Limit permissions** - Use role-based access control (RBAC)
5. **Monitor access** - Enable audit logging for sensitive operations

---

## Next Steps

### Immediate (Phase 2)
- [ ] T011: Create Redis connection utility
- [ ] T014-T019: Create SQLAlchemy models
- [ ] T020-T022: Create Alembic migrations

### Future Enhancements
- Add read replica support for scaling
- Implement database query logging
- Add connection pool metrics to Prometheus
- Create database session middleware for request tracing

---

## References

- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Neon DB Connection Guide](https://neon.tech/docs/guides/sqlalchemy)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [asyncpg Driver](https://magicstack.github.io/asyncpg/current/)

---

## Acceptance Criteria (T010)

- [x] Async SQLAlchemy 2.0+ with AsyncEngine
- [x] Connection pooling for Neon DB (serverless PostgreSQL)
- [x] Async session management with context manager
- [x] Proper error handling and logging
- [x] Environment variables for DATABASE_URL
- [x] FastAPI dependency injection (get_db)
- [x] Application startup/shutdown lifecycle
- [x] Health check integration
- [x] Comprehensive documentation
