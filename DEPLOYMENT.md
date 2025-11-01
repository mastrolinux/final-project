# Deployment Guide - Render.com

## Repository Successfully Migrated!

Your monorepo is now set up and pushed to GitHub at:
**https://github.com/mastrolinux/final-project**

## Next Step: Deploy to Render.com

### Step 1: Connect Repository to Render

1. Go to: **https://dashboard.render.com/**
2. Click: **"New +"** button (top right)
3. Select: **"Blueprint"**
4. If not already connected, click **"Connect GitHub"**
5. Authorize Render to access your repositories
6. Select repository: **"mastrolinux/final-project"**
7. Render will automatically detect the `render.yaml` file
8. Review the services it will create:
   - `identity-api-backend` (Python web service)
9. Click: **"Apply"**

### Step 2: Set Environment Variables

After the service is created:

1. Click on the **"identity-api-backend"** service
2. Go to the **"Environment"** tab (left sidebar)
3. Click **"Add Environment Variable"**
4. Add these variables one by one:

**Required Variables:**
```
SUPABASE_URL = your_supabase_project_url
SUPABASE_ANON_KEY = your_supabase_anon_key
SUPABASE_SERVICE_KEY = your_supabase_service_role_key
```

To get these values:

- Run `supabase status` in your backend directory
- Or go to your Supabase project dashboard > Settings > API

5. Click **"Save Changes"**

### Step 3: Wait for Deployment

The deployment will automatically start. You'll see:

- Build logs showing `pip install -r requirements.txt`
- The service starting with `uvicorn`
- Status will change to "Live" when ready (5-10 minutes)

### Step 4: Test Your API

Once deployed, test the health endpoint:

```bash
curl https://identity-api-backend.onrender.com/health
```

Or visit in browser:
**https://identity-api-backend.onrender.com/docs**

You should see the FastAPI Swagger documentation.

## Deployment Configuration

Your `render.yaml` is configured with:

- **Service Name**: identity-api-backend
- **Plan**: Free tier
- **Region**: Oregon
- **Root Directory**: backend/
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- **Health Check**: `/health` endpoint
- **Auto Deploy**: Enabled (deploys on every push to main)

## Auto-Deploy Feature

Every time you push to the `main` branch on GitHub, Render will automatically:

1. Pull the latest code
2. Run the build command
3. Restart the service
4. Health check the deployment

## Monitoring Your Deployment

In the Render dashboard, you can:

- View real-time logs
- See deployment history
- Monitor resource usage
- Set up alerts
- View metrics

## Adding Frontend Later

When you're ready to add the frontend:

1. Implement the frontend in the `frontend/` directory
2. Uncomment the frontend service in `render.yaml`
3. Push to GitHub
4. Render will automatically deploy both services

## Environment-Specific URLs

After deployment, update your local `.env` files:

**Backend (Production)**:
```
FRONTEND_URL=https://identity-frontend.onrender.com
```

**Frontend (when deployed)**:
```
VITE_API_URL=https://identity-api-backend.onrender.com
```

## Troubleshooting

### Build Fails
- Check the build logs in Render dashboard
- Verify `requirements.txt` is correct
- Check Python version matches (3.12)

### Service Won't Start
- Check the service logs
- Verify environment variables are set
- Check health endpoint is working

### Health Check Fails
- Ensure `/health` endpoint exists in your FastAPI app
- Check the endpoint returns 200 status
- Verify the app starts without errors

## Useful Commands

**View Logs Locally**:
```bash
cd backend
docker compose logs -f
```

**Test Locally Before Deploy**:
```bash
cd backend
docker compose up
curl http://localhost:8000/health
```

## Repository Structure

```
final-project/
├── backend/           -> Deploys to Render.com
├── frontend/          -> Will deploy to Render.com (when ready)
├── architecture/      -> Thesis documentation
├── render.yaml        -> Deployment configuration
└── README.md          -> Project overview
```

## Success Criteria

After successful deployment:

- [ ] Service shows "Live" status in Render
- [ ] Health endpoint returns 200: https://identity-api-backend.onrender.com/health
- [ ] API docs accessible: https://identity-api-backend.onrender.com/docs
- [ ] Logs show no errors
- [ ] Auto-deploy works on git push

---

**Your monorepo is ready for continuous deployment!**

Push to GitHub -> Render automatically deploys -> Service is live

