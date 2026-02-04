# EchoVerse Companion - Upgrade

This project has been upgraded with a modern React Frontend and a FastAPI Backend, ready for Vercel deployment.

## 🚀 How to Run Locally

### 1. Backend (API)
Open a terminal in the project root:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Backend Server
cd backend
python -m uvicorn main:app --reload
```
*Port: 8000*

### 2. Frontend (UI)
Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```
*Port: 5173 (usually)*

Open http://localhost:5173 to verify.

## 🌐 Deploying to Vercel (for WhatsApp)

To share this app via WhatsApp, you need to deploy it to the web.

1.  Push this code to your GitHub repository.
2.  Go to [Vercel](https://vercel.com) and "Add New Project".
3.  Import your `ECHOVERSA` repository.
4.  Vercel should automatically detect the configuration via `vercel.json`.
5.  Deploy!
6.  Copy the Vercel URL and share it on WhatsApp.

## ℹ️ Features

-   **Home Screen**: Detects if Local AI or External AI (OpenAI/Gemini) is being used and displays a privacy disclaimer.
-   **Local AI Fallback**: Uses local logic (or safe mock generation if models aren't downloaded) to ensure privacy.
-   **Glassmorphism UI**: Premium design.
