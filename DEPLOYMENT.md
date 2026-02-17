# Deployment Guide for Keto Meal Plan Generator

## Production Deployment Architecture

The application uses Render for hosting and consists of:

1. **Backend API Service** - FastAPI application serving the API
2. **PostgreSQL Database** - Neon DB for primary data storage
3. **Cleanup Cron Job** - Weekly automated cleanup tasks
4. **Frontend Application** - Next.js app (deployed separately)

## Environment Configuration

### Production Environment Variables

Create a production `.env.production` file with these variables:

```env
# Production Environment
ENV=production
APP_URL=https://your-frontend-domain.com

# Database (Neon PostgreSQL)
NEON_DATABASE_URL=postgresql://username:password@ep-xxx.us-east-1.aws.neon.tech/dbname

# Redis (for caching and rate limiting)
REDIS_URL=redis://user:password@host:port/db
UPSTASH_REDIS_REST_URL=https://your-redis-url.vercel.app
UPSTASH_REDIS_REST_TOKEN=your_rest_token

# Payment processing (Paddle)
PADDLE_API_KEY=your_paddle_api_key
PADDLE_WEBHOOK_SECRET=your_paddle_webhook_secret

# Email service (Resend)
RESEND_API_KEY=your_resend_api_key

# Cloud storage (Vercel Blob)
BLOB_READ_WRITE_TOKEN=your_vercel_blob_token

# AI Service (choose one or both)
OPEN_AI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# Security
ADMIN_API_KEY=your_production_admin_api_key_with_32_characters_min
ADMIN_IP_WHITELIST=your_server_ip,load_balancer_ip

# Sentry (error tracking)
SENTRY_BACKEND_DSN=https://your-sentry-dsn.sentry.io
SENTRY_RELEASE=keto-meal-plan-backend@1.0.0
```

### Setting Environment Variables on Render

For Render deployment, go to your service dashboard and set these Environment Variables:

- `ENV` = `production`
- `NEON_DATABASE_URL` = your Neon DB connection string
- `REDIS_URL` = your Redis connection URL
- `PADDLE_API_KEY` = your Paddle API key
- `PADDLE_WEBHOOK_SECRET` = your Paddle webhook secret
- `RESEND_API_KEY` = your Resend API key
- `BLOB_READ_WRITE_TOKEN` = your Vercel Blob token
- `OPEN_AI_API_KEY` or `GEMINI_API_KEY` = your AI API key
- `ADMIN_API_KEY` = your secure admin API key (32+ characters)
- `ADMIN_IP_WHITELIST` = comma-separated IP addresses for admin access
- `SENTRY_BACKEND_DSN` = Sentry DSN (optional but recommended)
- `SENTRY_RELEASE` = Release version for Sentry

## Deployment Process

### Backend Deployment

1. **Repository Setup**
   - Create a Render account and connect to your GitHub repository
   - Navigate to https://dashboard.render.com/select-repo to create a new web service

2. **Create Web Service**
   - Select your repository containing the Keto Meal Plan Generator
   - Choose "Web Service" type
   - Environment: Python
   - Build Command: `pip install -r requirements.txt && pip install -r requirements-prod.txt`
   - Start Command: `gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - Environment: Production
   - Region: Oregon (or closest to your users)

3. **Configure Environment Variables**
   - Add the required environment variables as described above

4. **Database Setup**
   - On Render, create a new "PostgreSQL" instance
   - Connect it to your web service
   - The database connection string will be auto-populated

### Frontend Deployment

1. **Vercel Setup** (or use Render Web Service)
   - Deploy frontend to Vercel
   - Set environment variable: `NEXT_PUBLIC_API_BASE_URL` = your backend URL

2. **Environment Variables for Frontend**
   - `NEXT_PUBLIC_API_BASE_URL`: Your backend API URL (e.g., `https://your-backend.onrender.com/api/v1`)

### Cron Job Setup

The cleanup cron job runs every Sunday at 3 AM UTC to:
- Remove old quiz responses (older than 30 days)
- Clean up expired magic links (older than 24 hours)
- Delete old payment transactions (older than 90 days)
- Remove old blacklist entries (older than 180 days)
- Clean up old meal plans (older than 180 days)
- Remove old manual resolution items (older than 365 days)

## Production Configuration

### Database Migrations

Run database migrations after deployment:

```bash
# For production, you may need to run the migration manually after deployment
# This is typically done automatically via the deployment process
python -m alembic upgrade head
```

### Health Checks

The application provides these health check endpoints:
- `GET /health` - Basic health check
- `GET /` - Root endpoint with service status

### Rate Limiting

The application implements rate limiting:
- Quiz start: 8 requests per minute per IP
- Quiz submission: 4 requests per minute per IP
- Download endpoints: Rate-limited per user
- Recovery endpoints: Rate-limited per IP

### Security Configuration

1. **Admin Access Control**
   - Admin endpoints locked behind API key
   - Optional IP whitelisting via `ADMIN_IP_WHITELIST`
   - Admin API key should be 32+ characters

2. **Payment Webhook Security**
   - Paddle webhook signatures validated
   - Idempotency for webhook processing

3. **Error Tracking**
   - Sentry setup for error monitoring
   - Health check endpoints filtered out of error reporting

## Deployment Commands

### Running Locally in Production Mode

```bash
# Set production environment
export ENV=production

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-prod.txt

# Run the application
python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT
# Or with gunicorn
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### Manual Cleanup (if needed)

```bash
# Run cleanup job manually (for testing or on-demand)
python scripts/cleanup/cleanup_cron.py --dry-run  # Test run without deletions
python scripts/cleanup/cleanup_cron.py           # Run actual cleanup
```

## Load Testing

Run load tests before production deployment:

```bash
# Test with 20 concurrent users for 5 minutes
python scripts/load_test.py --users 20 --duration 5 --base-url https://your-backend.onrender.com

# Production load test (100 users for 10 minutes)
python scripts/load_test.py production
```

## Security Testing

Run security tests to validate deployment:

```bash
# Run security tests
python -m pytest tests/security/ -v
```

## Monitoring and Maintenance

### Production Monitoring

The application includes:
- Sentry error tracking
- Request/response logging
- Performance monitoring via request durations
- Health check endpoints

### Data Retention Policy

- Quiz responses: Deleted after 30 days
- Magic links: Expire after 24 hours
- Payment transactions: Kept for 90 days
- Email blacklist: Kept for 180 days
- Meal plans: Kept for 180 days
- Manual resolution: Kept for 365 days

### Manual Resolution Queue

The application includes a manual resolution system for chargebacks and special cases:
- Admin endpoint: `/api/v1/admin/resolve-issue`
- Issues tracked for SLA monitoring
- Automatic resolution after set time periods

## Troubleshooting

### Common Deployment Issues

1. **Database Connection Fails**
   - Verify `NEON_DATABASE_URL` is correct
   - Check if database instance is properly provisioned

2. **Environment Variables Not Loaded**
   - Confirm all required variables are set in Render dashboard
   - Check for typos in variable names

3. **AI Services Not Working**
   - Verify API keys are properly configured
   - Check that either `OPEN_AI_API_KEY` or `GEMINI_API_KEY` is set

4. **Cron Job Not Running**
   - Check if the schedule is correct
   - Verify environment variables are configured for the cron job

### Debugging in Production

For production debugging:
- Monitor Sentry dashboard for error reports
- Check application logs in Render dashboard
- Use health endpoints to verify service status
- Run smoke tests against production environment