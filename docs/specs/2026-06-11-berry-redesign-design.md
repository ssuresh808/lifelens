# LifeLens v4 "Berry" redesign, design spec

Date: 2026-06-11
Status: approved by product owner; awaiting implementation plan

## 1. Overview

LifeLens evolves from a camera-first scanning tool into a friendly everyday assistant built around **Berry**, a robot helper mascot. The app gains a conversational core (recipes from your ingredients, plus an ask-anything chatbot), a complete visual revamp (Fresh Mint palette, light and dark modes), saved conversations, and a settings panel. The proven photo-scanning flow remains as its own tab.

Goals, in the owner's words: inviting more than anything; an app you can go to with any life task; recipes from whatever is in your kitchen as the headline feature on phones; a full chatbot experience leading on desktop.

## 2. Visual identity

### Palette ("Fresh Mint")

| Token | Light | Dark |
|---|---|---|
| `--bg` | `#F3FAF7` | `#0E1F1B` |
| `--card` | `#FFFFFF` | `#1A302A` |
| `--text` | `#143029` | `#E3F2EB` |
| `--primary` | `#0EA5A0` | `#2DD4BF` |
| `--accent` (mint) | `#34D399` | `#86EFAC` |
| `--citrus` | `#FFC83D` | `#FFB13D` |
| `--header gradient` | `#0EA5A0 → #34D399` | same, slightly deepened |

- Rounded geometry everywhere: 14 to 26px radii, pill buttons, soft shadows.
- System font stack (no external font dependency; the current Google Fonts loader goes away).
- Theme: Light / Dark / Auto (follows `prefers-color-scheme`); selected in Settings; persisted in `localStorage`; default Auto.
- **Writing rule: no em dashes anywhere.** Not in UI copy, and Berry's prompts instruct him never to use them.

### Berry, the mascot

A round floating robot: chef hat (three puffs + band), perfectly circular teal body, oven-mitt hands, a belly screen showing a steaming pot, hover glow instead of feet.

| Aspect | Day (light mode) | Night (dark mode) |
|---|---|---|
| Body | `#0EA5A0`, no stroke | `#134E48` with `#2DD4BF` neon rim |
| Eyes | Soft pill shape, lagoon `#0B5563`, mint catchlight `#E0FBF4` | Soft pill shape, glowing aqua `#7BF5E3`, no pupils |
| Cheeks | Peach `#FFB4A2` at 75% | Peach `#FFB4A2` at 45% |
| Hat | White | Soft cream `#F2EFE4`, sparkles appear around him |
| Mitts | `#FFC83D` | `#FFB13D` |

Expressions: **default** (pills + smile), **delighted** (crescent eyes, used when serving the dish menu and recipes), **thinking** (eyes blink, belly-pot steam animates while waiting on the model). Respect `prefers-reduced-motion`.

Berry is implemented once as a React SVG component with props: `variant` (day/night), `mood` (default/delighted/thinking), `size`. Used in: header logo, chat avatars (38px white circle, Berry fills it), Scan empty state, loading states.

## 3. Information architecture

Three tabs. Camera/photo upload is available in all three.

| Surface | Order | Default tab | Navigation |
|---|---|---|---|
| Phone (< 900px) | Cook, Scan, Ask | **Cook** | Bottom tab bar; header has 🕘 history and ⚙️ settings top-right |
| Desktop (≥ 900px) | Ask, Scan, Cook | **Ask** | Left sidebar: brand, nav, ＋ New chat, Recent chats list, ⚙️ Settings pinned at bottom |

Rationale: phone users reach for it while cooking; laptop users come to ask.

### Greeting header

Time-aware greeting computed from the device clock (so it is automatically correct for the user's timezone): morning / afternoon / evening / late night variants, e.g. "Good evening! 👋 What's on your mind?" (Ask) and "What are we cooking tonight?" (Cook). No subtitle.

## 4. Screens

### 4.1 Cook (recipes from your ingredients)

Chat with Berry. Flow:

1. Berry greets, asks what's in the kitchen. User types ingredients or attaches a photo (fridge/pantry shot).
2. If spices were not mentioned, Berry asks once (salt and pepper assumed present).
3. If meal shape was not specified, Berry asks with quick-pick chips, tappable or answerable in text:
   - Time: ⚡ Quick (under 30 min) / 🍲 Take your time
   - Serving: 👤 Just me / 👥 For two / 👨‍👩‍👧 Family
4. Berry serves **5 to 10 dish cards**. Default spans many world cuisines; if the user names a culture, all dishes follow it. Each card: dish name, cuisine, minutes, serves, difficulty, "uses what you have" check, optional nice-to-add items. Dishes must be feasible with the stated ingredients plus pantry basics.
5. Tapping a card asks Berry for the full recipe: ingredient list with amounts scaled to the serving choice, numbered steps, time breakdown. Rendered as a recipe card in the chat.
6. Conversation continues freely (swap ingredients, make it spicier, no oven, etc.).

### 4.2 Scan

The existing flow restyled. Mode chips: ◎ Anything, ¶ Explain, ⚙ Fix-it, ✚ Nutrition, 文 Translate. **Plant doctor is removed.** Friendly capture card with Berry; camera/photo library on mobile, drag-and-drop and Ctrl/Cmd+V paste on desktop; optional note; 🌐 toggle; client-side downscale to 1400px stays. Results render in the existing single result-card path (category, title, confidence, summary, steps, warnings, sources, follow-ups).

### 4.3 Ask (general chatbot)

Open-ended chat with Berry about any life task. Berry's answers favor: a bolded direct answer first, numbered steps, a 🎯 goal line making the outcome concrete, and follow-up suggestion chips. Sources, when web search was used, appear as tappable link buttons that open in a new tab. Photos can be attached to any message.

### 4.4 Web search

Manual toggle (🌐) in the input bar of all three tabs, off by default (default changeable in Settings). When on, the backend enables the web search tool and Berry cites tappable sources.

### 4.5 Saved chats

- Every Cook/Ask conversation is saved automatically on the device (`localStorage`) from the first user message.
- Auto-titled from the first user message (trimmed to ~32 chars).
- Desktop: Recent chats list in the sidebar (icon 🍳 or 💬, relative time). Phone: same list in a drawer behind the 🕘 header button.
- ＋ New chat starts a fresh conversation; selecting an old chat restores its full history and continues it (history is replayed to the model).
- Scan results are not part of chat history (unchanged from today).
- Cap stored chats (e.g. 50 most recent); Clear chat history lives in Settings.

### 4.6 Settings

Opened from ⚙️ (bottom of sidebar on desktop, panel opens above it bottom-left; top-right header gear on phone, panel opens from that corner). Contents:

- Theme: Light / Dark / Auto
- Web search default: on/off
- Berry's tips on start: on/off (the greeting hint bubble)
- Clear chat history (with confirm)
- Footnote: sign-in and synced settings come later (no login system in this release)

Settings persist in `localStorage`.

## 5. Safety and content filtering

Strict filters for inappropriate images and conversations, owner requirement:

- Every system prompt (chat and scan) carries a firm safety section: politely refuse and redirect anything explicit, sexual, hateful, harassing, dangerous, or illegal, in text or images. Berry stays friendly, brief, and offers a constructive alternative ("I can't help with that, but I'm happy to...").
- The model's own built-in refusal behavior is the second layer.
- Refused exchanges are not written into saved chat history.
- The existing per-IP rate limit (20 requests/hour) remains as abuse protection.

## 6. Backend design

### 6.1 Unchanged

`POST /scan` keeps its contract, tests, rate limiting, and model (`LIFELENS_MODEL`, default `claude-sonnet-4-6`). The only change: the `plant` mode brief is removed from `MODE_BRIEFS` (requests with `mode="plant"` fall back to `auto`, which the existing fallback already handles; the `Mode` literal drops `plant`).

### 6.2 New: `POST /chat`

Request (Pydantic `ChatRequest`):

```json
{
  "tab": "cook" | "ask",
  "web_search": false,
  "messages": [
    {"role": "user" | "assistant", "text": "...",
     "image_base64": "optional", "media_type": "optional"}
  ]
}
```

Validation: 1 to 30 messages, each text ≤ 4000 chars; images only on user messages, max 5MB decoded each, max 2 images per request (older images are stripped client-side before sending); same media types as scan.

Response (Pydantic `ChatReply`), one contract for both tabs:

```json
{
  "message": "Berry's conversational reply",
  "dishes": [{"id": "slug", "name": "...", "cuisine": "...", "minutes": 25,
               "serves": 2, "difficulty": "easy", "have": ["..."], "nice_to_add": ["..."]}],
  "recipe": {"name": "...", "cuisine": "...", "minutes": 25, "serves": 2,
              "ingredients": [{"item": "...", "amount": "..."}], "steps": ["..."]},
  "chips": ["quick follow-up suggestions"],
  "goal": "optional 🎯 goal line (ask tab)",
  "sources": [{"title": "...", "url": "https://..."}]
}
```

`dishes`, `recipe`, `goal` are optional/empty by default. The model is instructed to return exactly this JSON; the existing tolerant first-`{`-to-last-`}` extraction and 502-on-parse-failure behavior are reused.

Implementation details:

- Model: `LIFELENS_CHAT_MODEL` env var, default `claude-opus-4-8`. Scan stays on Sonnet.
- Berry persona system prompt shared by both tabs (identity, warmth, no em dashes, safety section, JSON contract), plus tab briefs:
  - cook: the recipe flow rules from 4.1 (ask spices once, ask time/serving once, 5 to 10 feasible dishes, multicultural default, honor a named cuisine, scale amounts to serving choice).
  - ask: direct answer first, numbered steps, goal line, suggest follow-up chips, links only from web search.
- `web_search: true` adds the same `web_search_20250305` tool used by scan.
- httpx call mirrors `/scan`: 120s timeout, `(httpx.HTTPError, OSError)` caught to a retryable 502, `max_tokens` 4096.
- Shares the per-IP rate limiter with scan.

### 6.3 CLAUDE.md update

The architecture rules section is rewritten: two output contracts now exist (`ScanResult` for /scan, `ChatReply` for /chat), each with a single rendering path in the frontend. Key, prompts, and tools still live only in `backend/`.

## 7. Frontend architecture

Restructure from one 580-line `App.jsx` into focused modules (Vite + React, no new runtime dependencies):

```
frontend/src/
  App.jsx              shell: tab state, responsive layout, greeting
  theme.js             tokens, ThemeProvider, localStorage + system listener
  berry.jsx            Berry SVG component (variant, mood, size)
  api.js               scanImage() + sendChat()
  components/
    TabBar.jsx         bottom tabs (mobile) / sidebar (desktop)
    ChatView.jsx       shared chat surface for Cook and Ask
    Message.jsx        bubbles, Berry avatar, chips, source links
    DishCards.jsx      dish menu + recipe card rendering
    ScanView.jsx       restyled scan flow (logic ported as-is)
    ResultCard.jsx     existing scan result rendering, restyled
    SettingsPanel.jsx  settings UI
    ChatHistory.jsx    recent chats list / drawer
  storage.js           chats + settings persistence (versioned schema)
```

- `ChatView` is configured per tab (greeting, placeholder, starter chips) but renders through the same message components.
- Images in chat: client-side downscale reuses the existing `downscale()`; thumbnails render in the user's bubble.
- Errors render as a Berry bubble with a retry button ("My kitchen wifi hiccuped, try that again?").
- PWA manifest: update theme colors to Fresh Mint; name stays LifeLens.

## 8. Testing

- Backend (pytest, target ≥ 20 tests): ChatRequest validation (tab values, message caps, image rules), prompt construction (persona + tab briefs + safety section + no-em-dash rule present, web search clause only when enabled), ChatReply round-trip including dishes/recipe shapes, /chat 502 paths (network error, unparseable reply), plant mode removed (falls back to auto), existing scan tests untouched.
- Frontend: `npm run build` green; manual checklist per tab on phone + desktop widths, both themes.
- Live verification before push: real /chat conversation (cook flow to a full recipe; ask flow with web search) against the dev backend.

## 9. Out of scope (later milestones)

Accounts and synced settings; streaming responses; voice input; recipe images; push notifications; server-side moderation API as a third safety layer; scan history persistence.

## 10. Rollout

Same infrastructure (Render backend, Vercel frontend, /scan rewrite). New env var `LIFELENS_CHAT_MODEL` set in Render. Standard discipline: small green commits, DEVLOG milestone entries, README screenshot refresh after ship.
