import { useEffect, useRef, useState } from "react";
import { sendChat } from "../api.js";
import { downscale } from "../image.js";
import { BerryAvatar } from "../berry.jsx";
import { saveChat, titleFrom } from "../storage.js";
import Message from "./Message.jsx";

const OPENERS = {
  cook: "Hey, I'm Berry 🍳 What's in your kitchen? Type your ingredients or snap a photo of your fridge.",
  ask: "Hi, I'm Berry 👋 Ask me anything: paperwork, plans, repairs, decisions. Attach a photo if it helps.",
};

// Tappable meal preferences (cook tab). Selecting highlights the chip; nothing
// is typed into the input. The choice rides along invisibly with the next send.
const COOK_PREFS = {
  time: [
    { id: "quick", label: "⚡ Quick, under 30 min", note: "a quick meal, under 30 minutes" },
    { id: "slow", label: "🍲 Take your time", note: "no rush, happy to take our time" },
  ],
  serves: [
    { id: "solo", label: "👤 Just me", note: "cooking for one" },
    { id: "two", label: "👥 For two", note: "cooking for two" },
    { id: "family", label: "👨‍👩‍👧 Family", note: "cooking for the family, four or more" },
  ],
};

export default function ChatView({ tab, chat, setChat, variant, webDefault, tipsOnStart = true }) {
  const [input, setInput] = useState("");
  const [image, setImage] = useState(null);
  const [web, setWeb] = useState(webDefault);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [prefs, setPrefs] = useState({ time: null, serves: null });
  const fileRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => { setWeb(webDefault); }, [webDefault]);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [chat.messages, busy]);

  useEffect(() => {
    const onPaste = async (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
      if (item) setImage(await downscale(item.getAsFile()));
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  const togglePref = (group, id) =>
    setPrefs((p) => ({ ...p, [group]: p[group] === id ? null : id }));

  const selectedPrefs = () =>
    Object.entries(COOK_PREFS)
      .map(([group, opts]) => opts.find((o) => o.id === prefs[group]))
      .filter(Boolean);

  // Berry sees the tapped chips as a bracketed note on the outgoing message;
  // the chat transcript and input bar stay clean.
  const prefContext = () => {
    const sel = selectedPrefs();
    return tab === "cook" && sel.length
      ? `[Meal preferences selected in the app: ${sel.map((o) => o.note).join("; ")}]`
      : "";
  };

  const send = async (text) => {
    const body = (text ?? input).trim();
    const context = prefContext();
    if ((!body && !image && !context) || busy) return;
    setError("");
    // Sending chips alone still shows something human in the transcript.
    const shown = body || (image ? "" : selectedPrefs().map((o) => o.label).join(" · "));
    const userMsg = { role: "user", text: shown, image };
    const messages = [...chat.messages, userMsg];
    const updated = { ...chat, title: chat.title || titleFrom(shown || "📷 photo"), messages };
    setChat(updated);
    saveChat(updated);
    setInput("");
    setImage(null);
    setBusy(true);
    try {
      const reply = await sendChat({ tab, webSearch: web, messages, context });
      const done = { ...updated, messages: [...messages, { role: "assistant", reply }] };
      setChat(done);
      saveChat(done);
    } catch (err) {
      setError(err.message || "Something hiccuped. Try again?");
    } finally {
      setBusy(false);
    }
  };

  const pickDish = (dish) => send(`Full recipe for ${dish.name}, please.`);

  // The failed user message is already in chat.messages; just re-ask Berry.
  const retry = async () => {
    if (busy || chat.messages.length === 0) return;
    setError("");
    setBusy(true);
    try {
      const reply = await sendChat({ tab, webSearch: web, messages: chat.messages, context: prefContext() });
      const done = { ...chat, messages: [...chat.messages, { role: "assistant", reply }] };
      setChat(done);
      saveChat(done);
    } catch (err) {
      setError(err.message || "Something hiccuped. Try again?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="chat-scroll">
        {tipsOnStart && (
          <div className="row">
            <BerryAvatar variant={variant} />
            <div className="bubble-bot">{OPENERS[tab]}</div>
          </div>
        )}
        {chat.messages.map((m, i) => (
          <Message key={i} m={m} variant={variant} onChip={send} onPickDish={pickDish} />
        ))}
        {busy && (
          <div className="row">
            <BerryAvatar variant={variant} mood="thinking" />
            <div className="bubble-bot">…</div>
          </div>
        )}
        {error && (
          <div className="error">
            {error} <button className="chip" onClick={retry}>Retry</button>
          </div>
        )}
        <div ref={endRef} />
      </div>
      {tab === "cook" && (
        <div className="prefbar">
          {Object.entries(COOK_PREFS).map(([group, opts]) =>
            opts.map((o) => (
              <button
                key={o.id}
                className={`chip ${prefs[group] === o.id ? "on" : ""}`}
                aria-pressed={prefs[group] === o.id}
                onClick={() => togglePref(group, o.id)}
              >
                {o.label}
              </button>
            ))
          )}
        </div>
      )}
      <div className="inputbar">
        <button className="ibtn" title="Attach a photo" onClick={() => fileRef.current?.click()}>📷</button>
        {image && <img src={image.dataUrl} alt="" style={{ height: 34, borderRadius: 8 }} />}
        <textarea
          rows={1}
          value={input}
          placeholder={tab === "cook" ? "List ingredients or snap your fridge…" : "Ask Berry anything…"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <button className={`ibtn ${web ? "on" : ""}`} title="Search online" onClick={() => setWeb((w) => !w)}>🌐</button>
        <button className="send" onClick={() => send()} disabled={busy}>➤</button>
      </div>
      <input ref={fileRef} type="file" accept="image/*" capture="environment" style={{ display: "none" }}
        onChange={async (e) => { const f = e.target.files?.[0]; if (f) setImage(await downscale(f)); e.target.value = ""; }} />
    </>
  );
}
