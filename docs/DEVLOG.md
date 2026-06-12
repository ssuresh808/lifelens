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

## Milestone 5 — Deployment to production

**Built:** LifeLens is now live at https://lifelens-two.vercel.app. The backend runs on Render with the API key held as a server-side secret and CORS locked to the frontend origin; the frontend is a PWA on Vercel, installable on iOS, Android, Mac, and Windows. A `/scan` rewrite on Vercel proxies to the Render service, so the browser only ever talks to one origin.

**Why:** A deployed app is a real product; localhost is a demo. Every platform (iPhone, Android, Mac, Windows) can now access the same codebase with appropriate input methods (camera on phones, paste on laptops).

**Problem solved:** The app is no longer theoretical — it's on the internet and can be shared with anyone. Two deployment-day gotchas worth recording: Vercel's default deployment protection shipped the site behind a login wall (disabled in project settings — a public app must be publicly viewable), and Render assigned `lifelens-3y5q.onrender.com` rather than the service name the rewrite guessed, so the rewrite had to be repointed. The full production path was verified with a real scan: structured high-confidence result in ~17s.

**Next:** Add mobile-specific polish (viewport meta tags, splash screens), streaming responses so results render as they arrive, and conversation follow-ups so users can ask clarification questions without retaking a photo.

## Milestone 6 — The Berry redesign: from scanner to companion

**Built:** A complete reimagining of the app around Berry, a round chef-hatted robot helper. LifeLens is now a three-tab assistant: Cook (tell Berry what's in your kitchen, by text or fridge photo, and get 5 to 10 feasible dishes from world cuisines, then tap one for a full scaled recipe), Scan (the original camera modes, minus plant doctor), and Ask (an open chatbot for any life task, with numbered steps, a concrete goal line, and tappable cited sources). New `/chat` backend endpoint with a strict ChatReply JSON contract and a separate chat model (Opus class) from the scan model (Sonnet class); conversations are saved on-device with a history sidebar; Fresh Mint design system with light, dark, and auto themes; settings panel; strict safety rules in every prompt. Phones open on Cook with bottom tabs; desktops open on Ask with a sidebar. Backend suite grew from 14 to 42 tests.

**Why:** The scanner proved the structured-output architecture, but a camera-only app meets people in one moment. The brief for this milestone: an inviting app you can bring any life task to, leading with what's-in-my-kitchen cooking on phones and ask-anything on desktops. One shared chat surface powers both conversations, the same way one result card powered every scan mode.

**Problems solved along the way:** Two production blockers were caught in final review despite a fully green suite. The Vercel rewrite file only proxied `/scan`, so the new chat would have 404'd on deploy. Worse, the frontend stored Berry's replies as structured objects but sent only their (empty) text back upstream, so the model never saw its own prior turns, and dropping those turns produced consecutive same-role messages the upstream API rejects: every conversation would have died on turn two. A test had even locked in the broken behavior. Both were fixed, and a live smoke test now exercises the full cook-to-recipe and ask-with-search flows against the real API before any deploy.

**Next:** Streaming responses, saved scan history, README screenshots of the new design, and richer Berry moods (he already has day and night shifts, lagoon eyes by day and an aqua glow after dark).

## Milestone 7 — First real users, first real bugs

**Built:** A post-launch polish round driven entirely by live phone testing. The app shell now fills the real mobile viewport (dynamic viewport height, so iOS Safari's collapsing URL bar no longer leaves a dead half-screen below the tab bar) and the tab bar stays pinned to the bottom. The Cook meal chips became real controls: tap to highlight (one pick per group, tap again to clear), the input bar stays empty, and the selection rides along with the next message as a bracketed note only Berry sees, with a prompt rule so he treats taps as answers and never re-asks. Berry got a personality while thinking: three dots bouncing in a wave and a full hop-and-spin, eyes still blinking mid-air. The chat input grows line by line as you type instead of scrolling inside a one-line box.

**Why:** Screenshots from a real phone found what the desktop browser never showed. The biggest catch: every recipe tap failed with "Berry got tongue-tied," and each retry made it worse.

**Problems solved:** That recipe failure was two stacked bugs. First, the model occasionally emits a literal line break inside a JSON string, which Python's strict parser rejects; parsing now runs lenient (strict=False) on both endpoints. Second, and nastier: a failed turn left the orphaned user message in history, so the next tap sent two user messages in a row, which the upstream API rejects, so every later turn failed too. One transient hiccup bricked the whole conversation. The backend now merges consecutive same-role messages before calling the model; the exact failure conversation from the bug report is a regression test, and the same payload was replayed against production to confirm the fix.

When a third intermittent failure surfaced anyway, the patch-by-patch approach gave way to a structural rule: the user always gets Berry's words. Replies validate against forgiving schemas (a dish without an id, "25 min" as a string, ingredients as plain strings are all accepted), and anything that still fails walks a salvage chain: repair trailing commas, recover the message field from the parsed dict, regex it out of broken JSON, or fall back to the raw text. Only a literally empty reply is an error now, and six tests pin down every salvage path.

**Next:** Streaming responses, saved scan history, and README screenshots of the current design.
