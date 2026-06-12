/** localStorage persistence for settings and saved chats. Versioned, defensive. */

const SETTINGS_KEY = "lifelens.settings.v1";
const CHATS_KEY = "lifelens.chats.v1";
const MAX_CHATS = 50;

const DEFAULT_SETTINGS = { theme: "auto", webSearchDefault: false, tipsOnStart: true };

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage full or denied */ }
}

export function getSettings() {
  return { ...DEFAULT_SETTINGS, ...read(SETTINGS_KEY, {}) };
}

export function saveSettings(patch) {
  const next = { ...getSettings(), ...patch };
  write(SETTINGS_KEY, next);
  return next;
}

export function listChats() {
  return read(CHATS_KEY, []);
}

export function saveChat(chat) {
  const chats = listChats().filter((c) => c.id !== chat.id);
  chats.unshift({ ...chat, updatedAt: Date.now() });
  write(CHATS_KEY, chats.slice(0, MAX_CHATS));
}

export function clearChats() {
  write(CHATS_KEY, []);
}

export function newChat(tab) {
  return { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, tab, title: "", messages: [] };
}

export function titleFrom(text) {
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > 32 ? t.slice(0, 31) + "…" : t || "New chat";
}
