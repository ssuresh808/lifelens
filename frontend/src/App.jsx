import { useState, useRef, useEffect } from "react";
import { scanImage } from "./api.js";

// ─── LifeLens v2 · point your camera at anything ───────────────────────────
// Production build, v3. Cross-platform input: camera capture on iOS/Android,
// drag-and-drop and clipboard paste on Mac/Windows. All model calls go
// through the backend (/scan); keys, prompts, and search tooling stay server-side.

const MODES = [
  { id: "auto", label: "Anything", icon: "◎", hint: "Identify and help with whatever this is" },
  { id: "plant", label: "Plant doctor", icon: "❧", hint: "Diagnose sick plants" },
  { id: "document", label: "Explain this", icon: "¶", hint: "Bills, letters, forms" },
  { id: "fixit", label: "Fix-it guide", icon: "⚙", hint: "Appliances & error codes" },
  { id: "nutrition", label: "Nutrition", icon: "✚", hint: "Labels & meals" },
  { id: "translate", label: "Translate", icon: "文", hint: "Signs & documents" },
];

// Phone cameras produce 8–12 MB images; the API caps around 5 MB.
// Downscale to max 1400px and re-encode as JPEG before sending.
function downscale(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const MAX = 1400;
      const scale = Math.min(1, MAX / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
      URL.revokeObjectURL(url);
      resolve({ dataUrl, mediaType: "image/jpeg", base64: dataUrl.split(",")[1] });
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Couldn't read that image.")); };
    img.src = url;
  });
}

const C = {
  base: "#161D1B",
  surface: "#202927",
  line: "#33403C",
  brass: "#E8A33D",
  paper: "#E9EDE3",
  ink: "#1C2422",
  good: "#8FBF7F",
  warn: "#E07A5F",
  dim: "#8FA09A",
};

export default function LifeLens() {
  const [mode, setMode] = useState("auto");
  const [image, setImage] = useState(null);
  const [note, setNote] = useState("");
  const [webSearch, setWebSearch] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | ready | scanning | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    const l = document.createElement("link");
    l.rel = "stylesheet";
    l.href =
      "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap";
    document.head.appendChild(l);
    return () => document.head.removeChild(l);
  }, []);

  const handleFile = async (file) => {
    if (!file || !file.type.startsWith("image/")) return;
    try {
      const img = await downscale(file);
      setImage(img);
      setResult(null);
      setError("");
      setPhase("ready");
    } catch (err) {
      setError(err.message);
      setPhase("error");
    }
  };

  const onPick = (e) => handleFile(e.target.files?.[0]);

  // Laptop workflow: paste a screenshot straight from the clipboard.
  useEffect(() => {
    const onPaste = (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) =>
        i.type.startsWith("image/")
      );
      if (item) handleFile(item.getAsFile());
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dragProps = {
    onDragOver: (e) => { e.preventDefault(); setDragging(true); },
    onDragLeave: () => setDragging(false),
    onDrop: (e) => {
      e.preventDefault();
      setDragging(false);
      handleFile(e.dataTransfer.files?.[0]);
    },
  };

  const scan = async () => {
    if (!image) return;
    setPhase("scanning");
    setError("");
    try {
      const parsed = await scanImage({
        mode,
        mediaType: image.mediaType,
        base64: image.base64,
        note: note.trim(),
        webSearch,
      });
      parsed.sources = Array.isArray(parsed.sources) ? parsed.sources : [];
      setResult(parsed);
      setHistory((h) =>
        [{ title: parsed.title, category: parsed.category, mode }, ...h].slice(0, 5)
      );
      setPhase("done");
    } catch (err) {
      console.error(err);
      setError(
        err.message?.startsWith("API:")
          ? `${err.message}. Try a smaller/clearer photo.`
          : "Couldn't read the result. Tap Scan again — or turn on Search online for tougher subjects."
      );
      setPhase("error");
    }
  };

  const reset = () => {
    setImage(null);
    setResult(null);
    setNote("");
    setError("");
    setPhase("idle");
    if (fileRef.current) fileRef.current.value = "";
  };

  const confColor =
    result?.confidence === "high" ? C.good : result?.confidence === "low" ? C.warn : C.brass;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: C.base,
        color: C.paper,
        fontFamily: "'Space Grotesk', system-ui, sans-serif",
      }}
    >
      <style>{`
        @keyframes sweep { 0% { top: 8% } 50% { top: 88% } 100% { top: 8% } }
        @keyframes pulse { 0%,100% { opacity: .4 } 50% { opacity: 1 } }
        @media (prefers-reduced-motion: reduce) { .sweep-line { animation: none !important; } }
        button:focus-visible, textarea:focus-visible { outline: 2px solid ${C.brass}; outline-offset: 2px; }
        textarea::placeholder { color: ${C.dim}; }
        .ll-shell { max-width: 520px; margin: 0 auto; padding: 20px 16px 48px; }
        .ll-placeholder { display: none; }
        @media (min-width: 900px) {
          .ll-shell { max-width: 1080px; display: grid; grid-template-columns: 1.05fr .95fr; column-gap: 32px; align-items: start; }
          .ll-head { grid-column: 1 / -1; }
          .ll-placeholder {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            min-height: 300px; border: 1px dashed ${C.line}; border-radius: 12px;
            color: ${C.dim}; font-size: 14px; text-align: center; padding: 24px; margin-bottom: 22px;
          }
        }
      `}</style>

      <div className="ll-shell">
        <header className="ll-head" style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 18 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em", margin: 0 }}>
            Life<span style={{ color: C.brass }}>Lens</span>
          </h1>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: C.dim }}>
            {webSearch ? "MODE · " + mode.toUpperCase() + " + WEB" : "MODE · " + mode.toUpperCase()}
          </span>
        </header>

        <div className="ll-left">
        {/* Mode chips */}
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 10, marginBottom: 6 }}>
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              style={{
                flex: "0 0 auto",
                padding: "8px 14px",
                borderRadius: 999,
                border: `1px solid ${mode === m.id ? C.brass : C.line}`,
                background: mode === m.id ? "rgba(232,163,61,0.12)" : "transparent",
                color: mode === m.id ? C.brass : C.dim,
                fontSize: 13,
                fontFamily: "inherit",
                cursor: "pointer",
              }}
              title={m.hint}
            >
              <span style={{ marginRight: 6 }}>{m.icon}</span>
              {m.label}
            </button>
          ))}
        </div>

        {/* Online search toggle */}
        <button
          onClick={() => setWebSearch((w) => !w)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: "10px 14px",
            marginBottom: 14,
            borderRadius: 10,
            border: `1px solid ${webSearch ? C.brass : C.line}`,
            background: webSearch ? "rgba(232,163,61,0.10)" : "transparent",
            color: webSearch ? C.brass : C.dim,
            fontSize: 13.5,
            fontFamily: "inherit",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <span style={{ fontSize: 16 }}>{webSearch ? "◉" : "○"}</span>
          <span>
            <strong style={{ display: "block", fontWeight: 600 }}>Search online</strong>
            <span style={{ fontSize: 12 }}>
              If the lens isn't sure, it looks it up on the web and cites sources
            </span>
          </span>
        </button>

        {/* Viewfinder */}
        <div
          {...dragProps}
          style={{
            position: "relative",
            borderRadius: 12,
            background: C.surface,
            outline: dragging ? `2px dashed ${C.brass}` : "none",
            outlineOffset: -6,
            minHeight: 300,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            marginBottom: 14,
          }}
        >
          {[
            { top: 10, left: 10, bt: 1, bl: 1 },
            { top: 10, right: 10, bt: 1, br: 1 },
            { bottom: 10, left: 10, bb: 1, bl: 1 },
            { bottom: 10, right: 10, bb: 1, br: 1 },
          ].map((p, i) => (
            <span
              key={i}
              style={{
                position: "absolute",
                width: 26,
                height: 26,
                top: p.top,
                left: p.left,
                right: p.right,
                bottom: p.bottom,
                borderTop: p.bt ? `2px solid ${C.brass}` : "none",
                borderLeft: p.bl ? `2px solid ${C.brass}` : "none",
                borderRight: p.br ? `2px solid ${C.brass}` : "none",
                borderBottom: p.bb ? `2px solid ${C.brass}` : "none",
                zIndex: 2,
                pointerEvents: "none",
              }}
            />
          ))}

          {image ? (
            <img
              src={image.dataUrl}
              alt="Your capture"
              style={{ width: "100%", maxHeight: 380, objectFit: "contain", display: "block" }}
            />
          ) : (
            <button
              onClick={() => fileRef.current?.click()}
              style={{
                background: "transparent",
                border: "none",
                color: C.dim,
                fontFamily: "inherit",
                cursor: "pointer",
                textAlign: "center",
                padding: 40,
              }}
            >
              <div style={{ fontSize: 40, color: C.brass, marginBottom: 10 }}>◎</div>
              <div style={{ fontSize: 15, color: C.paper }}>Point at anything</div>
              <div style={{ fontSize: 12.5, marginTop: 6, lineHeight: 1.5 }}>
                a plant · a bill · an error code · a bird
                <br />
                a landmark · a gadget · a label · a mystery
              </div>
              <div style={{ fontSize: 12, marginTop: 10, color: C.dim }}>
                Tap for camera/photos · drag an image here
                <br />
                or paste a screenshot (Ctrl/Cmd+V)
              </div>
              <div
                style={{
                  marginTop: 16,
                  display: "inline-block",
                  padding: "10px 22px",
                  borderRadius: 999,
                  background: C.brass,
                  color: C.ink,
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Take or choose a photo
              </div>
            </button>
          )}

          {phase === "scanning" && (
            <div
              className="sweep-line"
              style={{
                position: "absolute",
                left: "6%",
                right: "6%",
                height: 2,
                background: `linear-gradient(90deg, transparent, ${C.brass}, transparent)`,
                animation: "sweep 2.2s ease-in-out infinite",
                zIndex: 3,
              }}
            />
          )}
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={onPick}
          style={{ display: "none" }}
        />

        {/* Note / question */}
        {image && (
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Add a note or question (optional) — e.g. 'what breed is this?' or 'is this charge normal?'"
            style={{
              width: "100%",
              boxSizing: "border-box",
              background: C.surface,
              border: `1px solid ${C.line}`,
              borderRadius: 10,
              color: C.paper,
              fontFamily: "inherit",
              fontSize: 14,
              padding: "10px 12px",
              marginBottom: 12,
              resize: "vertical",
            }}
          />
        )}

        {/* Readout strip */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 11,
            color: C.dim,
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 16,
            animation: phase === "scanning" ? "pulse 1.2s infinite" : "none",
          }}
        >
          <span>
            {phase === "idle" && "STANDBY"}
            {phase === "ready" && "FRAME LOCKED · READY"}
            {phase === "scanning" && (webSearch ? "ANALYZING + SEARCHING…" : "ANALYZING…")}
            {phase === "done" && `RESULT · CONFIDENCE ${result?.confidence?.toUpperCase()}`}
            {phase === "error" && "SCAN FAILED"}
          </span>
          <span>{new Date().toLocaleDateString()}</span>
        </div>

        {/* Actions */}
        {image && phase !== "scanning" && (
          <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
            <button
              onClick={scan}
              style={{
                flex: 1,
                padding: "14px 0",
                borderRadius: 10,
                border: "none",
                background: C.brass,
                color: C.ink,
                fontWeight: 700,
                fontSize: 15,
                fontFamily: "inherit",
                cursor: "pointer",
              }}
            >
              {phase === "done" || phase === "error" ? "Scan again" : "Scan it"}
            </button>
            <button
              onClick={reset}
              style={{
                padding: "14px 18px",
                borderRadius: 10,
                border: `1px solid ${C.line}`,
                background: "transparent",
                color: C.dim,
                fontSize: 14,
                fontFamily: "inherit",
                cursor: "pointer",
              }}
            >
              Retake
            </button>
          </div>
        )}

        {/* Error */}
        {phase === "error" && (
          <div
            style={{
              border: `1px solid ${C.warn}`,
              borderRadius: 10,
              padding: 14,
              color: C.warn,
              fontSize: 14,
              marginBottom: 20,
              lineHeight: 1.5,
            }}
          >
            {error}
          </div>
        )}

        </div>

        <div className="ll-right">
        {/* Desktop placeholder before first result */}
        {!result && (
          <div className="ll-placeholder">
            <div style={{ fontSize: 28, color: "#33403C", marginBottom: 10 }}>◎</div>
            Your result card appears here.
            <br />
            Drop an image or paste a screenshot to begin.
          </div>
        )}

        {/* Result card */}
        {result && phase === "done" && (
          <article
            style={{
              background: C.paper,
              color: C.ink,
              borderRadius: 12,
              padding: 18,
              marginBottom: 22,
            }}
          >
            <div
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 11,
                letterSpacing: "0.08em",
                color: "#5C6A63",
                marginBottom: 6,
              }}
            >
              {result.category?.toUpperCase()}
              <span style={{ float: "right", color: confColor, fontWeight: 600 }}>
                ● {result.confidence}
              </span>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 8px", letterSpacing: "-0.01em" }}>
              {result.title}
            </h2>
            <p style={{ fontSize: 14.5, lineHeight: 1.55, margin: "0 0 14px" }}>{result.summary}</p>

            {result.steps?.length > 0 && (
              <>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: "0.08em", color: "#5C6A63", marginBottom: 8 }}>
                  WHAT TO KNOW / DO
                </div>
                <ol style={{ margin: "0 0 14px", paddingLeft: 20 }}>
                  {result.steps.map((s, i) => (
                    <li key={i} style={{ fontSize: 14, lineHeight: 1.5, marginBottom: 6 }}>{s}</li>
                  ))}
                </ol>
              </>
            )}

            {result.warnings?.length > 0 && (
              <div style={{ borderLeft: `3px solid ${C.warn}`, paddingLeft: 10, marginBottom: 12 }}>
                {result.warnings.map((w, i) => (
                  <p key={i} style={{ fontSize: 13.5, margin: "4px 0", color: "#8A4A38" }}>{w}</p>
                ))}
              </div>
            )}

            {result.sources?.length > 0 && (
              <>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: "0.08em", color: "#5C6A63", marginBottom: 6 }}>
                  FOUND ONLINE
                </div>
                <ul style={{ margin: "0 0 12px", paddingLeft: 18 }}>
                  {result.sources.map((s, i) => (
                    <li key={i} style={{ fontSize: 13, marginBottom: 4 }}>
                      <a href={s.url} target="_blank" rel="noreferrer" style={{ color: "#3D6B5C" }}>
                        {s.title || s.url}
                      </a>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {result.followUp?.length > 0 && (
              <p style={{ fontSize: 13, color: "#5C6A63", margin: 0 }}>
                Next: {result.followUp.join(" · ")}
              </p>
            )}
          </article>
        )}

        {/* History */}
        {history.length > 0 && (
          <div>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: "0.08em", color: C.dim, marginBottom: 8 }}>
              RECENT SCANS
            </div>
            {history.map((h, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "8px 0",
                  borderBottom: `1px solid ${C.line}`,
                  fontSize: 13.5,
                }}
              >
                <span>{h.title}</span>
                <span style={{ color: C.dim, fontSize: 12 }}>{h.category}</span>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
