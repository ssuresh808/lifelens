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
