# Architecture

LifeLens is deliberately small: two services, one contract, no framework sprawl. This document explains the decisions a reviewer might ask about.

## The shape of the system

A React PWA captures a photo and posts it to a FastAPI service, which forwards it to a multimodal LLM and returns a validated, structured result. The phone never holds a model API key, never sees a raw model response, and never has to parse free-form text.

## Decision 1: prompts live on the server

The expert personas and the JSON output contract are defined in `backend/app/prompts.py`, not in the client. Three reasons. First, prompt changes ship without a frontend deploy. Second, the prompt is part of the API's behavioral contract — if the schema in the prompt and the Pydantic model in `models.py` drift apart, the test suite catches it in one place. Third, prompts are intellectual property in a real product; keeping them server-side is the habit worth demonstrating.

## Decision 2: one output contract for every mode

A plant diagnosis, a bill explanation, and an appliance fix all return the same shape: `category`, `title`, `confidence`, `summary`, `steps[]`, `warnings[]`, `followUp[]`. This is the highest-leverage choice in the codebase. The frontend has exactly one result component, the backend has exactly one response model, and adding a new expert mode means writing one new persona string. The cost is that some modes slightly bend their content to fit the shape (a translation renders its text in `summary` and `steps`), which is an acceptable trade for a system this size.

## Decision 3: the model is treated as an unreliable upstream

LLMs occasionally return malformed JSON, wrap output in markdown fences, or add preamble despite instructions. The backend strips fences, parses defensively, and validates against the Pydantic schema. A parse failure is logged with the raw output and surfaced to the client as a `502` with a human-readable message — the app tells the user to rescan rather than crashing or showing raw model text. Confidence is part of the contract too: the prompt instructs the model to self-report `low` confidence on unclear images, and the UI renders that honestly instead of pretending certainty.

## Decision 4: defense at the edge

The `/scan` endpoint validates before it spends money: base64 integrity, a 5 MB decoded size cap, an allow-list of image media types, and a fixed-window per-IP rate limit (20 scans/hour) all run before any upstream call. The rate limiter is in-process and resets on restart — the right call for a single-instance deployment, and the documented upgrade path is Redis with a sliding window when there's more than one replica.

## Decision 5: shrink images before they leave the phone

Modern phone cameras produce 8-12 MB photos; vision APIs cap around 5 MB and charge by input size. The frontend downscales every capture to a 1400px maximum dimension on a canvas and re-encodes as JPEG before upload. This fixed the most common real-world failure (oversized payloads silently rejected upstream), cut latency roughly in half, and costs nothing in diagnostic quality at these resolutions.

## Decision 6: web search as an opt-in tool, declared server-side

When the user enables "Search online," the backend attaches the web_search tool to the model call and the system prompt instructs the model to search only when uncertain or when the answer needs current information - then to report the pages it used in a `sources` array that is part of the same response schema. The tool declaration lives server-side with the prompts, so search behavior can be tuned (or budgeted) without a client release, and the frontend renders sources with one small addition to the existing result card.

## What I would build next

Streaming responses so the summary renders before the steps finish generating; an optional follow-up turn ("ask about this result") that reuses the image and prior analysis as context; IndexedDB scan history so the PWA is useful offline; and image downscaling on-device before upload to cut latency and cost. Each of these is scoped so none would change the core contract.
