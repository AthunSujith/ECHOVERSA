# Deploying ECHOVERSA to Vercel

## Prerequisites
1. **GitHub Account**: Ensure your project is pushed to GitHub (which you have done).
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com).

## Deployment Steps

1. **Log in to Vercel**.
2. **Add New Project**:
   - Click **"Add New..."** -> **"Project"**.
   - Import your GitHub repository: `AthunSujith/ECHOVERSA`.

3. **Configure Project**:
   - **Framework Preset**: Select **Vite**.
   - **Root Directory**: Leave as `./` (Project Root).
   - **Build Command**: `cd frontend && npm install && npm run build` (This is already in package.json, so Vercel might auto-detect or you can override).
   - **Output Directory**: `frontend/dist`.
   - **Install Command**: `cd frontend && npm install` (if needed, but usually automatic).

4. **Environment Variables**:
   Add the following environment variables in the Vercel dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `GEMINI_API_KEY`: Your Google Gemini API key (optional).

5. **Deploy**:
   - Click **Deploy**.
   - Vercel will build the frontend and set up the Python backend serverless functions in `/api`.

6. **Verify**:
   - Visit the provided Vercel URL.
   - The backend API will typically be available at `/api/generate`.

## Troubleshooting
- If the backend 404s, ensure `api/index.py` exists (I created it for you) and `vercel.json` is in the root.
- Ensure the `rewrites` in `vercel.json` are correct.
