# Alembic Migrations - Quick Reference

## Essential Commands

All commands run from `backend/` directory with virtual environment activated.

### Setup Verification
```bash
# Verify setup is correct
python database/migrations/verify_setup.py
```

### Check Status
```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --verbose
```

### Create Migrations
```bash
# Auto-generate migration from model changes (recommended)
alembic revision --autogenerate -m "Add users table"

# Create empty migration (for data migrations)
alembic revision -m "Migrate user preferences"
```

### Apply Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply next migration only
alembic upgrade +1

# Apply to specific revision
alembic upgrade <revision_id>
```

### Rollback Migrations
```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Testing Migrations
```bash
# Show SQL without executing
alembic upgrade head --sql

# Test upgrade/downgrade cycle
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Common Workflows

### Creating a New Model
1. Create/modify model in `database/models/`
2. Generate migration: `alembic revision --autogenerate -m "Add model"`
3. Review generated migration in `database/migrations/versions/`
4. Test migration: `alembic upgrade head`
5. Verify changes in database
6. Commit migration file to git

### Rolling Back Changes
1. Identify target revision: `alembic history`
2. Rollback: `alembic downgrade <revision_id>`
3. Verify database state
4. Fix issues and create new migration

### Database Reset (Development Only)
```bash
# WARNING: Destroys all data
alembic downgrade base
alembic upgrade head
```

## Migration File Structure

```python
"""Add users table

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2026-01-03 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abc123def456'
down_revision = 'previous_revision_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop table
    op.drop_table('users')
```

## Best Practices

### DO
- Review auto-generated migrations before applying
- Test both upgrade and downgrade paths
- Use descriptive migration messages
- Keep migrations small and focused
- Commit migration files to version control
- Run migrations in CI/CD pipeline

### DON'T
- Edit migration files after they've been applied
- Delete migration files from versions/ directory
- Skip migrations (use alembic stamp if needed)
- Add migrations with same revision ID
- Hardcode values (use environment variables)

## Troubleshooting

### "Can't locate revision identified by 'xyz'"
```bash
# Check migration history
alembic history
# Stamp database to specific revision
alembic stamp <revision_id>
```

### "Multiple head revisions are present"
```bash
# Merge branches
alembic merge -m "Merge migrations" <rev1> <rev2>
```

### Database connection issues
```bash
# Verify environment variable
echo $NEON_DATABASE_URL
# Check .env file
cat backend/.env | grep NEON_DATABASE_URL
```

### Import errors
```bash
# Ensure venv is activated
source .venv/bin/activate
# Verify working directory
pwd  # should be /path/to/backend/
```

## Environment Configuration

Required environment variable in `backend/.env`:
```bash
NEON_DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'
```

Automatically converted to asyncpg format:
```bash
postgresql+asyncpg://user:pass@host/db?ssl=require
```

## Next Steps

1. **Phase 2**: Create SQLAlchemy models
2. **Update env.py**: Import Base metadata
3. **Generate migration**: `alembic revision --autogenerate -m "Initial schema"`
4. **Review & test**: Verify generated SQL
5. **Apply**: `alembic upgrade head`

## Support

For detailed documentation, see:
- `database/migrations/README.md` - Full documentation
- `database/migrations/verify_setup.py` - Setup verification script
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
