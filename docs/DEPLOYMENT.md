# Deployment — making LifeLens a real, live app

This guide takes the repo from "runs on localhost" to a public URL that works on any iPhone, Android phone, Mac, or Windows laptop. Total time is roughly 30 minutes, and both services below have free tiers.

## 1. Backend → Render

Render runs the FastAPI service and holds your API key as a secret.

1. Push this repo to GitHub.
2. Go to render.com → New → Web Service → connect your GitHub repo.
3. Settings:
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment variables:
   - `ANTHROPIC_API_KEY` — your key from console.anthropic.com
   - `LIFELENS_CORS_ORIGINS` — your frontend URL once you have it (step 2), e.g. `https://lifelens.vercel.app`
5. Deploy. Note the URL, e.g. `https://lifelens-api.onrender.com`. Check `https://<your-api>/health` returns `{"status": "ok"}`.

## 2. Frontend → Vercel

1. In `frontend/src/api.js`, change the fetch URL from `"/scan"` to `import.meta.env.VITE_API_URL + "/scan"` (or add a rewrite — see note below).
2. Go to vercel.com → Add New Project → import the same GitHub repo.
3. Settings: root directory `frontend`, framework preset Vite.
4. Environment variable: `VITE_API_URL=https://lifelens-api.onrender.com`.
5. Deploy. Your app is now live at `https://<project>.vercel.app`.

Simpler alternative: add a `vercel.json` in `frontend/` with a rewrite from `/scan` to your Render URL, and `api.js` needs no change:

```json
{ "rewrites": [{ "source": "/scan", "destination": "https://lifelens-api.onrender.com/scan" }] }
```

## 3. Install it like a native app

Because LifeLens is a PWA with a manifest, the live URL installs to the home screen or dock:

- **iPhone/iPad:** open in Safari → Share → Add to Home Screen
- **Android:** open in Chrome → menu → Add to Home screen / Install app
- **Mac:** Safari → File → Add to Dock (or Chrome → Install)
- **Windows:** Edge or Chrome → Install app icon in the address bar

After this, LifeLens launches full-screen with its own icon on all four platforms — one codebase, no app stores.

## 4. Post-deploy checklist

- Update `LIFELENS_CORS_ORIGINS` on Render to the exact Vercel URL (no trailing slash).
- Test a camera scan on a phone and a paste-screenshot scan on a laptop against the live URL.
- Add the live URL to the top of the README and take fresh screenshots for it.
- Log the deployment as a milestone in `docs/DEVLOG.md` and push.

## Costs and limits to know

Render's free tier sleeps after inactivity — first scan after a quiet period takes ~30s while it wakes. The per-IP rate limit (20 scans/hour) in `backend/app/main.py` protects your API spend; each scan with a downscaled image costs roughly a cent. Watch usage at console.anthropic.com.
