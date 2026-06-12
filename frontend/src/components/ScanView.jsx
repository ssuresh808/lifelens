import { useEffect, useRef, useState } from "react";
import { scanImage } from "../api.js";
import { downscale } from "../image.js";
import Berry from "../berry.jsx";
import ResultCard from "./ResultCard.jsx";

const MODES = [
  { id: "auto", label: "◎ Anything" },
  { id: "document", label: "¶ Explain" },
  { id: "fixit", label: "⚙ Fix-it" },
  { id: "nutrition", label: "✚ Nutrition" },
  { id: "translate", label: "文 Translate" },
];

export default function ScanView({ variant, webDefault }) {
  const [mode, setMode] = useState("auto");
  const [image, setImage] = useState(null);
  const [note, setNote] = useState("");
  const [web, setWeb] = useState(webDefault);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => { setWeb(webDefault); }, [webDefault]);

  useEffect(() => {
    const onPaste = async (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
      if (item) load(await downscale(item.getAsFile()));
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  const load = (img) => { setImage(img); setResult(null); setError(""); };

  const scan = async () => {
    if (!image || busy) return;
    setBusy(true);
    setError("");
    try {
      const parsed = await scanImage({ mode, mediaType: image.mediaType, base64: image.base64, note: note.trim(), webSearch: web });
      parsed.sources = Array.isArray(parsed.sources) ? parsed.sources : [];
      setResult(parsed);
    } catch (err) {
      setError(err.message || "Couldn't read the result. Try again?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="modechips">
        {MODES.map((m) => (
          <button key={m.id} className={`chip ${mode === m.id ? "on" : ""}`} onClick={() => setMode(m.id)}>
            {m.label}
          </button>
        ))}
      </div>
      <div
        className={`capture ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={async (e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f?.type.startsWith("image/")) load(await downscale(f));
        }}
      >
        {image ? (
          <img src={image.dataUrl} alt="Your capture" />
        ) : (
          <>
            <Berry variant={variant} size={86} />
            <b>Show me anything!</b>
            <span style={{ fontSize: 12.5, color: "var(--muted)", whiteSpace: "pre-line" }}>
              {"a bill · an error code · a label · a sign\ntap below, drag an image here, or paste (Ctrl/Cmd+V)"}
            </span>
            <button className="cta" onClick={() => fileRef.current?.click()}>📷 Take or choose a photo</button>
          </>
        )}
      </div>
      <div className="inputbar">
        <button className="ibtn" title="Attach a photo" onClick={() => fileRef.current?.click()}>📷</button>
        <textarea rows={1} value={note} placeholder="Add a note or question (optional)…"
          onChange={(e) => setNote(e.target.value)} />
        <button className={`ibtn ${web ? "on" : ""}`} title="Search online" onClick={() => setWeb((w) => !w)}>🌐</button>
        <button className="send" onClick={scan} disabled={!image || busy}>{busy ? "…" : "➤"}</button>
      </div>
      {image && !busy && (
        <button className="chip" style={{ alignSelf: "flex-start" }} onClick={() => { setImage(null); setResult(null); }}>
          ↺ Retake
        </button>
      )}
      {error && <div className="error">{error}</div>}
      {result && <ResultCard result={result} />}
      <input ref={fileRef} type="file" accept="image/*" capture="environment" style={{ display: "none" }}
        onChange={async (e) => { const f = e.target.files?.[0]; if (f) load(await downscale(f)); e.target.value = ""; }} />
    </>
  );
}
