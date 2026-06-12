export default function ResultCard({ result }) {
  const conf = result.confidence === "high" ? "var(--accent)"
    : result.confidence === "low" ? "var(--danger)" : "var(--citrus)";
  return (
    <article className="resultcard">
      <div className="cat">
        <span>{result.category?.toUpperCase()}</span>
        <span style={{ color: conf, fontWeight: 700 }}>● {result.confidence}</span>
      </div>
      <h2>{result.title}</h2>
      <p style={{ margin: "0 0 10px" }}>{result.summary}</p>
      {result.steps?.length > 0 && (
        <ol style={{ margin: "0 0 10px", paddingLeft: 20 }}>
          {result.steps.map((s, i) => <li key={i} style={{ marginBottom: 5 }}>{s}</li>)}
        </ol>
      )}
      {result.warnings?.map((w, i) => <p key={i} className="warn">{w}</p>)}
      {result.sources?.length > 0 && (
        <div>
          {result.sources.map((s, i) =>
            /^https?:\/\//i.test(s.url) ? (
              <a key={i} className="srclink" href={s.url} target="_blank" rel="noreferrer">
                🔗 {s.title || s.url} ↗
              </a>
            ) : (
              <span key={i} className="srclink">🔗 {s.title || s.url}</span>
            )
          )}
        </div>
      )}
      {result.followUp?.length > 0 && (
        <p style={{ fontSize: 13, color: "var(--muted)", margin: "10px 0 0" }}>
          Next: {result.followUp.join(" · ")}
        </p>
      )}
    </article>
  );
}
