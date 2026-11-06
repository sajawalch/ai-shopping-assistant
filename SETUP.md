# Setup (Windows, PowerShell) - do these in order

You need Python 3.10+ and Node.js LTS (nodejs.org). Use two terminals.

## Terminal 1 - backend
    cd backend
    pip install -r requirements.txt
    copy .env.example .env          (then open .env and paste your OpenAI key after OPENAI_API_KEY=)
    uvicorn api:app --reload --port 8000

Check: open http://127.0.0.1:8000/api/health  ->  {"status":"ok","openai_key_set":true,"search_provider":"tavily"}
search_provider must say "tavily" for reliable results (add TAVILY_API_KEY to .env; free key at tavily.com).
"duckduckgo" works locally but is often blocked on hosting servers.
If openai_key_set is false, the key in .env is missing or misspelled.

## Terminal 2 - frontend
    cd frontend
    npm install
    npm run dev

Open http://localhost:5173 (use the address the terminal prints).

## Common problems
- 'vite' is not recognized        -> run npm install first, inside the frontend folder.
- Request failed (404)            -> the file must be named vite.config.js (not .json); restart npm run dev.
- Request failed (500) + message  -> read the message in the red box; usually the API key or an old file.
- Blank grey page                 -> press F12, open Console, read the red error.
- Not chosen yet never changes    -> backend/payload.py is the old version; use the one in this folder.
