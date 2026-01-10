# Deployment Architecture

**Last Updated**: 2026-01-01
**Status**: Finalized

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│                       (Vercel)                              │
│                                                             │
│  - Next.js 14.x + React + TypeScript                       │
│  - Quiz UI, Payment Integration, Dashboard                 │
│  - Deployed from GitHub (auto-deploy on push)              │
│  - URL: https://keto-meal-plan.vercel.app                  │
│  - Free Tier: 100GB bandwidth/month                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS API Calls
                       │ (CORS configured)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│                       (Render) ⭐                           │
│                                                             │
│  - FastAPI + Uvicorn                                       │
│  - AI Generation, PDF Creation, Webhooks, Cron Jobs        │
│  - Deployed from GitHub (manual trigger or auto)           │
│  - URL: https://keto-meal-plan-api.onrender.com            │
│  - Free Tier: Spins down after 15min (30s cold start)      │
│  - Paid Tier: $7/month (always-on, zero cold starts)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ├──► Neon DB (PostgreSQL)
                       ├──► Redis (Upstash/Redis Cloud)
                       ├──► Vercel Blob (PDF Storage)
                       ├──► OpenAI/Gemini (AI Generation)
                       ├──► Paddle (Payments)
                       ├──► Resend (Email)
                       └──► Sentry (Error Tracking)
```

---

## 📊 Why Render for Backend?

### ✅ Pros (Why Render Wins)

1. **No Timeout Limits**
   - AI generation: 15-20s
   - PDF generation: 3-20s
   - Total pipeline: 40-60s typical
   - **Vercel Hobby would timeout at 10s** ❌
   - **Render handles easily** ✅

2. **Native Cron Job Support**
   - cleanup-paid-quiz (every 6 hours)
   - cleanup-pdfs (daily)
   - cleanup-magic-links (daily)
   - check-sla-breaches (every 15 minutes) - CRITICAL
   - **Render has built-in cron** ✅
   - **Vercel needs paid plan or external service** ❌

3. **Cost-Effective**
   - Free tier: $0/month (acceptable for MVP with cold starts)
   - Paid tier: $7/month (always-on, production-ready)
   - **Vercel Pro: $20/month** for 50s timeout

4. **Predictable Performance**
   - SLA monitoring requires reliable 15-minute intervals
   - 4-hour SLA deadline requires consistent execution
   - Always-on server = predictable performance

5. **Better for Long-Running Processes**
   - Persistent server (not serverless)
   - Background jobs supported natively
   - WebSocket support if needed later

### ⚠️ Cons (Minor Trade-offs)

- Free tier cold start: ~30s after 15min inactivity (acceptable for MVP)
- Separate platform from frontend (industry-standard pattern)
- Need to manage server updates (automatic anyway)

---

## 🚀 Deployment Configuration

### Frontend (Vercel)

**Repository**: GitHub (auto-deploy on push to main)

**Build Settings**:
```bash
Build Command: npm run build
Output Directory: .next
Install Command: npm install
```

**Environment Variables** (Vercel Dashboard):
```env
NEXT_PUBLIC_API_URL=https://keto-meal-plan-api.onrender.com/v1
NEXT_PUBLIC_PADDLE_VENDOR_ID=<paddle_vendor_id>
NEXT_PUBLIC_PADDLE_ENVIRONMENT=production
NEXT_PUBLIC_ENABLE_MID_QUIZ_AUTH=true
```

**Custom Domain**: keto-meal-plan.vercel.app → your-domain.com

---

### Backend (Render)

**Repository**: GitHub (manual deploy or auto on push)

**Service Type**: Web Service

**Environment**: Python 3.11+

**Build Command**:
```bash
pip install -r requirements.txt
alembic upgrade head
```

**Start Command**:
```bash
uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables** (Render Dashboard):
```env
# Environment
ENV=production
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://...@neon.tech/...
REDIS_URL=redis://...

# AI APIs
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...

# Payment
PADDLE_API_KEY=...
PADDLE_WEBHOOK_SECRET=...

# Storage & Email
BLOB_READ_WRITE_TOKEN=vercel_blob_...
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=noreply@ketomealplan.com

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Auth
JWT_SECRET=<256-bit-secret>

# App
APP_URL=https://keto-meal-plan.vercel.app
```

**Health Check Path**: `/health`

---

### Cron Jobs (Render Dashboard)

Configure these in Render under "Cron Jobs":

```yaml
# Cleanup paid quiz responses
Name: cleanup-paid-quiz
Command: python scripts/cleanup_paid_quiz.py
Schedule: 0 */6 * * *

# Cleanup PDFs from Vercel Blob
Name: cleanup-pdfs
Command: python scripts/cleanup_pdfs.py
Schedule: 0 0 * * *

# Cleanup expired magic links
Name: cleanup-magic-links
Command: python scripts/cleanup_magic_links.py
Schedule: 0 2 * * *

# Check SLA breaches (CRITICAL)
Name: check-sla-breaches
Command: python scripts/sla_monitor.py
Schedule: */15 * * * *
```

---

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] All tests pass (`/test`)
- [ ] Security audit complete (`/audit-security`)
- [ ] Environment variables documented
- [ ] Database migrations ready
- [ ] Secrets rotated for production

### Frontend Deployment (Vercel)

- [ ] GitHub repository connected
- [ ] Environment variables set in Vercel dashboard
- [ ] Custom domain configured (optional)
- [ ] Deploy and verify build succeeds
- [ ] Test frontend: `https://keto-meal-plan.vercel.app`

### Backend Deployment (Render)

- [ ] GitHub repository connected
- [ ] Web Service created (Python environment)
- [ ] Start command configured: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- [ ] Environment variables set in Render dashboard
- [ ] Deploy and verify build succeeds
- [ ] Run migrations: `alembic upgrade head`
- [ ] Configure cron jobs in Render dashboard
- [ ] Test backend: `https://keto-meal-plan-api.onrender.com/health`

### Post-Deployment

- [ ] Update CORS origins in backend (allow Vercel frontend URL)
- [ ] Update `NEXT_PUBLIC_API_URL` in Vercel to Render backend URL
- [ ] Update Paddle webhook URL to Render backend
- [ ] Test full payment flow (Paddle test mode)
- [ ] Verify email delivery
- [ ] Check Sentry for errors
- [ ] Monitor Vercel Analytics
- [ ] Verify cron jobs run on schedule

---

## 🔗 URLs

| Service | Environment | URL |
|---------|-------------|-----|
| Frontend | Production | https://keto-meal-plan.vercel.app |
| Backend | Production | https://keto-meal-plan-api.onrender.com |
| API Docs | Production | https://keto-meal-plan-api.onrender.com/docs |
| Database | Production | Neon DB (serverless PostgreSQL) |
| Blob Storage | Production | Vercel Blob (https://blob.vercel-storage.com) |

---

## 💰 Cost Estimate

### Free Tier (MVP)

| Service | Cost | Limits |
|---------|------|--------|
| Vercel (Frontend) | $0/month | 100GB bandwidth, unlimited deployments |
| Render (Backend) | $0/month | 750 hours/month, spins down after 15min |
| Neon DB | $0/month | 0.5GB storage, 1 project |
| Vercel Blob | $0/month | 5GB storage |
| Resend | $0/month | 100 emails/day |
| **Total** | **$0/month** | Sufficient for MVP/testing |

### Paid Tier (Production)

| Service | Cost | Benefits |
|---------|------|----------|
| Vercel (Frontend) | $20/month (Pro) | 1TB bandwidth, analytics |
| Render (Backend) | $7/month (Starter) | Always-on, 512MB RAM, zero cold starts |
| Neon DB | $19/month (Pro) | 8GB storage, autoscaling |
| Vercel Blob | Included | 5GB included with Vercel Pro |
| Resend | $20/month | 50k emails/month |
| Redis (Upstash) | $10/month | 1GB storage |
| **Total** | **$76/month** | Production-ready, reliable |

---

## 🎯 Performance Targets

| Metric | Target | Render Free | Render Paid |
|--------|--------|-------------|-------------|
| Cold Start | <30s | ✅ ~30s | ✅ 0s (always-on) |
| API Latency | <500ms | ✅ | ✅ |
| Full Pipeline | <90s | ✅ 40-60s | ✅ 40-60s |
| Cron Reliability | 100% | ⚠️ 95% | ✅ 100% |
| Uptime | >99.5% | ⚠️ 99% | ✅ 99.9% |

**Recommendation**: Start with free tier, upgrade to paid ($7/month) when:
- Cold starts affect user experience
- Need guaranteed cron job execution
- Revenue justifies $7/month investment

---

## 📚 Related Documentation

- **Quickstart**: [quickstart.md](./quickstart.md) - Full deployment guide
- **Tasks**: [tasks.md](./tasks.md) - Task T139-T143 (Production Deployment)
- **Skills**: [/.claude/skills/deploy/SKILL.md](/.claude/skills/deploy/SKILL.md) - `/deploy` skill
- **Spec**: [spec.md](./spec.md) - External dependencies section

---

**Architecture Decision Record**: This deployment architecture was chosen based on:
1. Backend timeout requirements (40-60s pipeline vs Vercel's 10s limit)
2. Native cron job support for compliance (data retention)
3. Cost-effectiveness ($7/month vs $20/month for equivalent features)
4. Industry-standard pattern (Vercel + Render is widely adopted)
