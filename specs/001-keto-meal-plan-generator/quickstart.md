# Quickstart Guide: Keto Meal Plan Generator

**Feature Branch**: `001-keto-meal-plan-generator`
**Date**: 2025-12-30
**For**: Developers setting up local environment

---

## Prerequisites

### Required Software
- **Node.js**: 18.x or 20.x (for Next.js frontend)
- **Python**: 3.11+ (for FastAPI backend)
- **PostgreSQL**: 15+ (Neon DB compatible)
- **Redis**: 7.x+ (for distributed locks and rate limiting)
- **Git**: 2.x+

### Recommended Tools
- **npm/pnpm**: Package managers (pnpm recommended for speed)
- **pyenv/virtualenv**: Python version management
- **Docker** (optional): For local PostgreSQL and Redis containers
- **Postman/Insomnia**: API testing

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd ai-based-meal-plan
git checkout 001-keto-meal-plan-generator
```

### 2. Environment Variables

Create `.env.local` files for frontend and backend:

#### Frontend (.env.local)
```bash
# API Endpoints
NEXT_PUBLIC_API_URL=http://localhost:8000/v1

# Paddle (Payment)
NEXT_PUBLIC_PADDLE_VENDOR_ID=your_paddle_vendor_id
NEXT_PUBLIC_PADDLE_ENVIRONMENT=sandbox  # or "production"

# Feature Flags
NEXT_PUBLIC_ENABLE_MID_QUIZ_AUTH=true
```

#### Backend (.env)
```bash
# Environment
ENV=development  # or "production"

# Database (Neon DB or local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/keto_meal_plan

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI API (Production)
OPENAI_API_KEY=sk-proj-...

# Gemini API (Development/Testing)
GEMINI_API_KEY=AIzaSy...

# Paddle Payment
PADDLE_API_KEY=your_paddle_api_key
PADDLE_WEBHOOK_SECRET=your_paddle_webhook_secret

# Vercel Blob Storage
BLOB_READ_WRITE_TOKEN=vercel_blob_...

# Resend Email
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=noreply@ketomealplan.com

# Sentry (Error Tracking)
SENTRY_DSN=https://...@sentry.io/...

# JWT Secret (Account Authentication)
JWT_SECRET=your-256-bit-secret-key

# Application
APP_URL=http://localhost:3000
```

---

## Installation

### Frontend Setup (Next.js)

```bash
cd frontend

# Install dependencies
pnpm install
# or: npm install

# Run development server
pnpm dev
# Frontend runs on http://localhost:3000
```

### Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# Backend runs on http://localhost:8000
```

**Backend requirements.txt**:
```text
fastapi==0.110.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.6.0
python-dotenv==1.0.1
httpx==0.26.0
redis==5.0.1
reportlab==4.0.9
openai==1.12.0
openai-agents>=0.1.0,<1.0.0
bcrypt==4.1.2
python-jose[cryptography]==3.3.0
sentry-sdk[fastapi]==1.40.0
```

**Frontend package.json** (key dependencies):
```json
{
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "react-hook-form": "7.50.0",
    "zod": "3.22.4",
    "@hookform/resolvers": "3.3.4",
    "tailwindcss": "3.4.1",
    "framer-motion": "11.0.3",
    "lucide-react": "0.323.0",
    "@paddle/paddle-js": "1.2.0"
  },
  "devDependencies": {
    "typescript": "5.3.3",
    "@types/node": "20.11.5",
    "@types/react": "18.2.48"
  }
}
```

---

## Database Setup

### Option 1: Local PostgreSQL (Docker)

```bash
# Start PostgreSQL and Redis containers
docker-compose up -d

# Verify containers running
docker ps
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: keto_meal_plan
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Option 2: Neon DB (Cloud)

1. Sign up at [neon.tech](https://neon.tech)
2. Create new project: "keto-meal-plan-dev"
3. Copy connection string to `DATABASE_URL` in `.env`

### Run Migrations

```bash
cd backend

# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt"
```

**Expected Tables**:
- users
- quiz_responses
- meal_plans
- manual_resolution
- magic_link_tokens
- email_blacklist

---

## Testing Setup

### Backend Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Install test dependencies
pnpm add -D @testing-library/react @testing-library/jest-dom vitest

# Run tests
pnpm test
```

---

## Service Configuration

### Paddle (Payment Processing)

1. Sign up at [paddle.com](https://paddle.com)
2. Create sandbox account for testing
3. Configure webhook URL: `https://your-domain.com/webhooks/paddle`
4. Enable webhook events:
   - `payment.succeeded`
   - `payment.chargeback`
   - `payment.refunded`
5. Copy webhook secret to `PADDLE_WEBHOOK_SECRET`

### Vercel Blob (PDF Storage)

1. Create Vercel account and project
2. Enable Vercel Blob in project settings
3. Generate Read/Write token: `BLOB_READ_WRITE_TOKEN`
4. Set environment variable in `.env`

### Resend (Email Delivery)

1. Sign up at [resend.com](https://resend.com)
2. Verify sending domain: `ketomealplan.com`
3. Create API key: `RESEND_API_KEY`
4. Configure from address: `noreply@ketomealplan.com`

### Sentry (Error Tracking)

1. Create Sentry project
2. Copy DSN to `SENTRY_DSN`
3. Configure email alerts for:
   - Error rate >5%
   - Manual resolution queue entries
   - Payment webhook failures

---

## Running the Application

### Development Mode

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
pnpm dev

# Terminal 3: Redis (if not using Docker)
redis-server

# Terminal 4: PostgreSQL (if not using Docker/Neon)
postgres -D /usr/local/var/postgres
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (FastAPI Swagger UI)
- **Redoc**: http://localhost:8000/redoc

---

## Common Development Tasks

### Create New Database Migration

```bash
cd backend

# Make changes to SQLAlchemy models in src/models/
# Then generate migration
alembic revision --autogenerate -m "Add new column to users"

# Review generated migration in database/migrations/versions/
# Apply migration
alembic upgrade head
```

### Test Email Delivery Locally

```bash
# Use Resend test mode
# Emails sent to test@resend.dev will appear in dashboard
curl -X POST http://localhost:8000/internal/test-email \
  -H "Content-Type: application/json" \
  -d '{"to": "test@resend.dev"}'
```

### Test Paddle Webhook Locally

```bash
# Use ngrok to expose local backend
ngrok http 8000

# Configure Paddle webhook URL:
# https://your-ngrok-id.ngrok.io/webhooks/paddle

# Trigger test webhook from Paddle dashboard
```

### Test AI Generation

```bash
# Direct API call
curl -X POST http://localhost:8000/internal/generate-meal-plan \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "test_pay_123",
    "email": "test@example.com",
    "calorie_target": 1650,
    "preferences": {
      "excluded_foods": ["beef", "pork"],
      "preferred_proteins": ["chicken", "salmon"],
      "dietary_restrictions": "No dairy"
    }
  }'
```

### Clear Redis Cache

```bash
# Connect to Redis CLI
redis-cli

# Flush all keys (development only!)
FLUSHALL

# Clear specific pattern
KEYS payment_lock:*
DEL payment_lock:user@example.com
```

---

## Troubleshooting

### Issue: Database Connection Refused

**Solution**:
```bash
# Check PostgreSQL running
docker ps | grep postgres
# or
pg_isready -h localhost -p 5432

# Verify DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql+asyncpg://user:password@host:port/dbname
```

### Issue: Redis Connection Error

**Solution**:
```bash
# Check Redis running
redis-cli ping
# Should return: PONG

# Check Redis URL
echo $REDIS_URL
# Should be: redis://localhost:6379/0
```

### Issue: OpenAI/Gemini API Errors

**Solution**:
```bash
# Verify API key set
echo $OPENAI_API_KEY | head -c 10
# Should show: sk-proj-...

# Test API connectivity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: Frontend Can't Reach Backend

**Solution**:
```bash
# Verify backend running
curl http://localhost:8000/health

# Check NEXT_PUBLIC_API_URL in frontend/.env.local
cat frontend/.env.local | grep API_URL
# Should be: NEXT_PUBLIC_API_URL=http://localhost:8000/v1

# Check CORS settings in backend
# backend/src/main.py should allow http://localhost:3000
```

---

## Production Deployment

### Environment Preparation

1. **Frontend (Vercel)**:
   - Connect GitHub repository to Vercel
   - Set environment variables (NEXT_PUBLIC_API_URL, Paddle keys)
   - Deploy from `001-keto-meal-plan-generator` branch
   - Auto-deploys on git push

2. **Backend (Render)**:
   - Connect GitHub repository to Render
   - Create Web Service (Python environment)
   - Start command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
   - Set all environment variables in Render dashboard
   - Run migrations: `alembic upgrade head` (or use Render build command)
   - Configure cron jobs in Render dashboard for cleanup tasks

3. **Database (Neon DB Production)**:
   - Create production branch
   - Enable connection pooling
   - Configure backups

4. **Redis (Upstash or Redis Cloud)**:
   - Create production instance
   - Enable TLS
   - Configure connection limits

### Production Checklist

- [ ] All environment variables set (no defaults)
- [ ] Database migrations applied
- [ ] Paddle webhooks configured with production URL (Render backend URL)
- [ ] Vercel Blob production token configured
- [ ] Resend production domain verified
- [ ] Sentry DSN configured with email alerts
- [ ] HTTPS enabled (Vercel frontend, Render backend both handle automatically)
- [ ] CORS origins restricted to production domain (Vercel frontend URL)
- [ ] Rate limiting enabled (Redis)
- [ ] Scheduled jobs configured (data retention cleanup on Render cron jobs)

---

## Scheduled Jobs (Production)

Set up cron jobs on Render for data retention:

**Render Cron Jobs** (configured in Render dashboard):
```yaml
# Cleanup paid quiz responses (every 6 hours)
Name: cleanup-paid-quiz
Command: python scripts/cleanup_paid_quiz.py
Schedule: 0 */6 * * *

# Cleanup PDFs (daily at midnight UTC)
Name: cleanup-pdfs
Command: python scripts/cleanup_pdfs.py
Schedule: 0 0 * * *

# Cleanup magic links (daily at 2 AM UTC)
Name: cleanup-magic-links
Command: python scripts/cleanup_magic_links.py
Schedule: 0 2 * * *

# Check SLA breaches (every 15 minutes)
Name: check-sla-breaches
Command: python scripts/sla_monitor.py
Schedule: */15 * * * *
```

**Note**: Render provides native cron job support. Configure in Render dashboard under "Cron Jobs" section for your web service.

---

## Additional Resources

- **Spec**: [spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contracts**: [contracts/](./contracts/)
- **Research**: [research.md](./research.md)
- **OpenAI Agents SDK**: https://github.com/openai/openai-agents-python
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Next.js Docs**: https://nextjs.org/docs

---

## Support

For setup issues or questions:
- Review error logs: `backend/logs/` and Sentry dashboard
- Check API docs: http://localhost:8000/docs
- Consult constitution: `.specify/memory/constitution.md`

**Ready to start implementation? Run `/sp.tasks` to generate testable task breakdown.**
