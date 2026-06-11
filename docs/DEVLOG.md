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
