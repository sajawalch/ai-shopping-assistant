# Sahi Pick: laptop and phone advisor for Pakistan (LangGraph + FastAPI + React)

backend/   FastAPI + LangGraph agent
frontend/  React (Vite) interface

## Run locally
Backend:   see SETUP.md
Frontend:  cd frontend; npm install; npm run dev        (open http://localhost:5173)

## Deploy
1. Push this folder to GitHub (the .gitignore keeps your keys and node_modules out).
2. Backend on Render: New > Blueprint (uses render.yaml). Set OPENAI_API_KEY. Copy the service address.
3. Frontend on Vercel: import the repo, set Root Directory to `frontend`, add the environment variable
   VITE_API_URL = your Render address (no trailing slash). Deploy.
4. Back on Render, set ALLOWED_ORIGINS = your Vercel address, then redeploy the backend.
Notes: chats live in memory, so a backend restart ends open chats; run a single worker.
