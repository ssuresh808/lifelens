/** Client for the LifeLens backend. The Anthropic key never touches the phone. */
export async function scanImage({ mode, mediaType, base64, note = "", webSearch = false }) {
  const res = await fetch("/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode,
      media_type: mediaType,
      image_base64: base64,
      note,
      web_search: webSearch,
    }),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail;
    throw new Error(detail || `Scan failed (${res.status})`);
  }
  return res.json();
}

/** Send a Cook/Ask conversation turn. messages: [{role, text, image?}] where
 * image = {base64, mediaType}. Only the 2 most recent images are sent. */
export async function sendChat({ tab, webSearch, messages }) {
  const recent = messages.slice(-30);
  const wire = recent.map((m) => ({ role: m.role, text: m.text || "" }));
  let imagesLeft = 2;
  for (let i = recent.length - 1; i >= 0 && imagesLeft > 0; i--) {
    if (recent[i].role === "user" && recent[i].image) {
      wire[i].image_base64 = recent[i].image.base64;
      wire[i].media_type = recent[i].image.mediaType;
      imagesLeft--;
    }
  }
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tab, web_search: webSearch, messages: wire }),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail;
    throw new Error(detail || `Chat failed (${res.status})`);
  }
  return res.json();
}
