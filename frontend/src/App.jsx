import { useEffect, useMemo, useState } from "react";
import Berry from "./berry.jsx";
import ChatView from "./components/ChatView.jsx";
import ScanView from "./components/ScanView.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import { ChatList, HistoryDrawer } from "./components/ChatHistory.jsx";
import { getSettings, newChat, saveSettings } from "./storage.js";

const DESKTOP = "(min-width: 900px)";
const DARK = "(prefers-color-scheme: dark)";

function greeting(tab) {
  const h = new Date().getHours();
  const day = h < 5 ? "Up late?" : h < 12 ? "Good morning!" : h < 18 ? "Good afternoon!" : "Good evening!";
  if (tab === "cook") {
    const meal = h < 5 ? "Midnight snack?" : h < 11 ? "What's for breakfast?" : h < 16 ? "What's for lunch?" : "What are we cooking tonight?";
    return `${day} 🍳 ${meal}`;
  }
  if (tab === "scan") return `${day} 📷 Show me anything.`;
  return `${day} 👋 What's on your mind?`;
}

const TABS = [
  { id: "cook", icon: "🍳", label: "Cook" },
  { id: "scan", icon: "📷", label: "Scan" },
  { id: "ask", icon: "💬", label: "Ask" },
];

export default function LifeLens() {
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia(DESKTOP).matches);
  const [settings, setSettings] = useState(getSettings);
  const [tab, setTab] = useState(() => (window.matchMedia(DESKTOP).matches ? "ask" : "cook"));
  const [chats, setChats] = useState(() => ({ cook: newChat("cook"), ask: newChat("ask") }));
  const [showSettings, setShowSettings] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [systemDark, setSystemDark] = useState(() => window.matchMedia(DARK).matches);

  useEffect(() => {
    const mq = window.matchMedia(DESKTOP);
    const fn = (e) => setIsDesktop(e.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  useEffect(() => {
    const mq = window.matchMedia(DARK);
    const fn = (e) => setSystemDark(e.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  const dark = settings.theme === "dark" || (settings.theme === "auto" && systemDark);
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; }, [dark]);
  const variant = dark ? "night" : "day";

  const tabOrder = useMemo(
    () => (isDesktop ? ["ask", "scan", "cook"] : ["cook", "scan", "ask"]).map((id) => TABS.find((t) => t.id === id)),
    [isDesktop]
  );

  const updateSettings = (patch) => setSettings(saveSettings(patch));
  const setChat = (c) => setChats((prev) => ({ ...prev, [c.tab]: c }));
  const openChat = (c) => { setChats((prev) => ({ ...prev, [c.tab]: c })); setTab(c.tab); };
  const startNew = () => {
    const target = tab === "scan" ? "ask" : tab;
    setChats((prev) => ({ ...prev, [target]: newChat(target) }));
    if (tab === "scan") setTab("ask");
  };

  const view =
    tab === "scan" ? (
      <ScanView variant={variant} webDefault={settings.webSearchDefault} />
    ) : (
      <ChatView key={chats[tab].id} tab={tab} chat={chats[tab]} setChat={setChat}
        variant={variant} webDefault={settings.webSearchDefault}
        tipsOnStart={settings.tipsOnStart} />
    );

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><Berry variant={variant} size={36} /> LifeLens</div>
        {tabOrder.map((t) => (
          <button key={t.id} className={`nav-item ${tab === t.id ? "on" : ""}`} onClick={() => setTab(t.id)}>
            {t.icon} {t.label}
          </button>
        ))}
        <div style={{ marginTop: 12, overflowY: "auto", flex: 1 }}>
          <ChatList onOpen={openChat} onNew={startNew} />
        </div>
        <button className="nav-item settings-link" onClick={() => setShowSettings((s) => !s)}>⚙️ Settings</button>
      </aside>

      <div className="main-col">
        <header className="header mobile">
          <Berry variant={variant} size={30} />
          <span className="brand">LifeLens</span>
          <button className="hbtn" aria-label="Chat history" onClick={() => setShowHistory(true)}>🕘</button>
          <button className="hbtn" aria-label="Settings" onClick={() => setShowSettings((s) => !s)}>⚙️</button>
        </header>
        <div className="greeting"><b>{greeting(tab)}</b></div>
        <div className="view">{view}</div>
        <nav className="tabbar">
          {tabOrder.map((t) => (
            <button key={t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>
              <span className="ticon">{t.icon}</span>{t.label}
            </button>
          ))}
        </nav>
      </div>

      {showSettings && (
        <SettingsPanel placement={isDesktop ? "desktop" : "mobile"} settings={settings}
          onChange={updateSettings} onClose={() => setShowSettings(false)}
          onCleared={() => { setShowSettings(false); startNew(); }} />
      )}
      {showHistory && !isDesktop && (
        <HistoryDrawer onOpen={openChat} onNew={startNew} onClose={() => setShowHistory(false)} />
      )}
    </div>
  );
}
