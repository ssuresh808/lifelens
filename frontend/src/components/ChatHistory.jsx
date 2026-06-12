import { listChats } from "../storage.js";

function ago(ts) {
  const s = (Date.now() - ts) / 1000;
  if (s < 90) return "now";
  if (s < 3600) return `${Math.round(s / 60)}m`;
  if (s < 86400) return `${Math.round(s / 3600)}h`;
  if (s < 604800) return `${Math.round(s / 86400)}d`;
  return `${Math.round(s / 604800)}w`;
}

export function ChatList({ onOpen, onNew }) {
  const chats = listChats();
  return (
    <>
      <button className="newchat" onClick={onNew}>＋ New chat</button>
      <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: ".08em", color: "var(--muted)", margin: "2px 0 7px 4px" }}>
        RECENT CHATS
      </div>
      {chats.length === 0 && <div style={{ fontSize: 12.5, color: "var(--muted)", padding: 6 }}>No chats yet.</div>}
      {chats.map((c) => (
        <button key={c.id} className="hist" onClick={() => onOpen(c)}>
          <span>{c.tab === "cook" ? "🍳" : "💬"}</span>
          <span className="t">{c.title || "New chat"}</span>
          <span className="d">{ago(c.updatedAt)}</span>
        </button>
      ))}
    </>
  );
}

export function HistoryDrawer({ onOpen, onNew, onClose }) {
  return (
    <div className="histlist" onClick={onClose}>
      <div className="histpanel" onClick={(e) => e.stopPropagation()}>
        <ChatList onOpen={(c) => { onOpen(c); onClose(); }} onNew={() => { onNew(); onClose(); }} />
      </div>
    </div>
  );
}
