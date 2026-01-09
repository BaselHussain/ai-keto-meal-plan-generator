# Database Migrations

This directory contains Alembic migrations for the Keto Meal Plan Generator API.

## Directory Structure

```
database/
├── __init__.py              # Database package initialization
├── migrations/              # Alembic migrations directory
│   ├── env.py              # Alembic environment configuration
│   ├── script.py.mako      # Migration script template
│   ├── README.md           # This file
│   └── versions/           # Migration version files (auto-generated)
```

## Configuration

- **Database**: Neon DB (Serverless PostgreSQL)
- **ORM**: SQLAlchemy 2.0+ with async support
- **Migration Tool**: Alembic
- **Driver**: asyncpg for async PostgreSQL connections
- **Database URL**: Loaded from `NEON_DATABASE_URL` environment variable in `backend/.env`

## Environment Configuration

The `env.py` file is configured to:
- Load database URL from `NEON_DATABASE_URL` environment variable
- Convert standard PostgreSQL URL to asyncpg-compatible format
- Handle SSL/TLS connection parameters for Neon DB
- Support both online and offline migration modes
- Use async SQLAlchemy engine for migrations

## Common Commands

All commands should be run from the `backend/` directory.

### Check current migration revision
```bash
alembic current
```

### Create a new migration (auto-generate from model changes)
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Create a new empty migration
```bash
alembic revision -m "Description of changes"
```

### Apply all pending migrations
```bash
alembic upgrade head
```

### Rollback last migration
```bash
alembic downgrade -1
```

### Rollback to specific revision
```bash
alembic downgrade <revision_id>
```

### View migration history
```bash
alembic history --verbose
```

### Show SQL without executing (offline mode)
```bash
alembic upgrade head --sql
```

## Migration Best Practices

1. **Always review auto-generated migrations** - Alembic's autogenerate is helpful but not perfect
2. **Test migrations in both directions** - Always test both upgrade and downgrade paths
3. **Use descriptive migration messages** - Make it easy to understand what each migration does
4. **Add data migrations carefully** - Consider existing production data when adding constraints
5. **Keep migrations idempotent** - Migrations should be safe to run multiple times
6. **Version control** - All migration files should be committed to git

## Models Integration

When SQLAlchemy models are created (Phase 2), they should be imported in `env.py`:

```python
# In env.py, replace:
# target_metadata = None

# With:
from database.models import Base
target_metadata = Base.metadata
```

This enables Alembic's autogenerate feature to detect model changes.

## Database Connection

The database connection string is automatically loaded from the `NEON_DATABASE_URL` environment variable in `backend/.env`:

```
NEON_DATABASE_URL='postgresql://user:password@host/database?sslmode=require'
```

The `env.py` file automatically converts this to the asyncpg format:
```
postgresql+asyncpg://user:password@host/database?ssl=require
```

## Troubleshooting

### Connection Issues
- Verify `NEON_DATABASE_URL` is set correctly in `backend/.env`
- Ensure SSL parameters are included (Neon requires SSL)
- Check network connectivity to Neon DB

### Import Errors
- Ensure you're running commands from the `backend/` directory
- Verify virtual environment is activated
- Check that all required dependencies are installed

### Migration Conflicts
- Pull latest changes from git before creating new migrations
- Resolve merge conflicts in migration files carefully
- Consider using `alembic merge` for divergent migration branches

## Next Steps (Phase 2)

1. Create SQLAlchemy models in `database/models/`
2. Import Base metadata in `env.py`
3. Generate initial migration: `alembic revision --autogenerate -m "Initial schema"`
4. Review and test the migration
5. Apply migration: `alembic upgrade head`
