# DEVLOG — how LifeLens was built, step by step

A public journal of every milestone in this project. Newest entries at the bottom. Each entry says what was built, why, and what problem it solved — so anyone reading this repo can follow the whole journey.

---

## Milestone 1 — Project foundation

**Built:** FastAPI backend with a single `/scan` endpoint, Pydantic request/response schemas, per-mode prompt system with a shared JSON output contract, in-process rate limiting, and an 8-test pytest suite. React + Vite PWA frontend with a camera-first viewfinder UI and six expert modes (auto, plant, document, fix-it, nutrition, translate).

**Why:** Most AI demos are chat boxes. The goal was a product: photograph a real-world problem, get structured expert help. The key early decision was one output schema for every mode — it keeps the frontend to a single result component and makes new modes a five-line server change.

**Problem solved along the way:** Input validation originally ran after the server-config check, so a bad image returned a misleading 500. Reordered so client errors return 400s; caught by the test suite.

## Milestone 2 — Real phones broke it; fixed and expanded

**Built:** Client-side image downscaling (canvas, max 1400px, JPEG re-encode), tolerant JSON extraction (first `{` to last `}`), specific error messages, an "Anything" identify-everything mode, an optional note/question attached to each scan, and an opt-in "Search online" feature where the model uses an agentic web-search tool and returns cited sources inside the same schema. Test suite grew to 12.

**Why:** Real-device testing produced constant scan failures. Root cause: modern phone cameras shoot 8–12 MB photos, which exceeded the vision API's payload limit — the most valuable bug of the project, because it only appears with real hardware. The web-search feature came from a real user need: when the model isn't sure, it should be able to look it up rather than guess.

**Problem solved along the way:** With web search enabled, the model sometimes added prose around its JSON. The strict parser failed; the tolerant extractor fixed it without loosening the schema validation itself.

## Milestone 3 — Cross-platform: laptops join phones

**Built:** Drag-and-drop images onto the viewfinder, clipboard paste for screenshots (Ctrl/Cmd+V), a two-column responsive layout for screens ≥900px (controls and viewfinder left, results right), and a desktop empty-state that teaches the input methods. Camera capture remains the mobile path.

**Why:** The app should meet the image where it lives — on a phone that's the camera; on a Mac or Windows laptop it's a screenshot in the clipboard or a file on disk. Paste support in particular makes the laptop loop instant: screenshot → Cmd+V → scan.

---

<!-- Append new milestones below this line. Format: what was built, why, what problem it solved, what's next. One entry per pushed milestone. -->

## Milestone 4 — First live scans against the real API

**Built:** The repo went public on GitHub with CI (pytest + ruff + Vite build on every push), and the backend ran its first real scans against the live vision API — both the plain path and the "Search online" path, which returned a structured result with five cited sources inside the same schema.

**Why:** Everything before this milestone was verified against mocks. A real key and real images are where the remaining assumptions break, and they did — three ways.

**Problems solved along the way:** (1) The default model ID had been deprecated upstream and returned 404 on every scan; migrated to its documented replacement. (2) A transient TLS failure during the upstream call crashed the endpoint with an unhandled 500; the proxy now catches network-level errors — including the raw `ssl.SSLError` that httpx occasionally leaks unwrapped — and returns a retryable 502. (3) Web-search scans silently truncated mid-JSON at the old 1000-token output cap and could outlive the 60s upstream timeout; the budget is now 4096 tokens and the timeout 120s. Test suite grew to 14.

**Next:** Deploy the backend to Render and the frontend to Vercel per docs/DEPLOYMENT.md, then test camera scans and clipboard-paste scans on real devices against the live URL.
