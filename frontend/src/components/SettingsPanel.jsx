import { clearChats } from "../storage.js";

export default function SettingsPanel({ placement, settings, onChange, onClose, onCleared }) {
  return (
    <div className={`settings ${placement}`}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <b>⚙️ Settings</b>
        <button className="ibtn" onClick={onClose} style={{ background: "none", border: "none" }}>✕</button>
      </div>
      <div className="set-row">
        <span>Theme</span>
        <span className="seg">
          {["light", "dark", "auto"].map((t) => (
            <button key={t} className={settings.theme === t ? "on" : ""} onClick={() => onChange({ theme: t })}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </span>
      </div>
      <div className="set-row">
        <span>Web search default</span>
        <button className={`tog ${settings.webSearchDefault ? "on" : ""}`}
          onClick={() => onChange({ webSearchDefault: !settings.webSearchDefault })} aria-label="toggle web search" />
      </div>
      <div className="set-row">
        <span>Berry's tips on start</span>
        <button className={`tog ${settings.tipsOnStart ? "on" : ""}`}
          onClick={() => onChange({ tipsOnStart: !settings.tipsOnStart })} aria-label="toggle tips" />
      </div>
      <div className="set-row">
        <span>Clear chat history</span>
        <button style={{ color: "var(--danger)", fontWeight: 700, background: "none", border: "none" }}
          onClick={() => { if (window.confirm("Delete all saved chats on this device?")) { clearChats(); onCleared(); } }}>
          Clear…
        </button>
      </div>
      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 10 }}>
        Sign-in and synced settings come later.
      </div>
    </div>
  );
}
