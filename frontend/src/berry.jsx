/** Berry, the LifeLens mascot. variant: day|night, mood: default|delighted|thinking. */

const C = {
  day:   { body: "#0EA5A0", rim: "none",    eye: "#0B5563", spark: "#E0FBF4",
           cheek: "rgba(255,180,162,.75)", hat: "#FFFFFF", hatLine: "#D8E8E0",
           mitt: "#FFC83D", glow: "#34D399", screen: "#10231F", pot: "#5EEAD4",
           smile: "#0B5563" },
  night: { body: "#134E48", rim: "#2DD4BF", eye: "#7BF5E3", spark: "none",
           cheek: "rgba(255,180,162,.45)", hat: "#F2EFE4", hatLine: "#C9C2A8",
           mitt: "#FFB13D", glow: "#2DD4BF", screen: "#0B1A17", pot: "#7BF5E3",
           smile: "#7BF5E3" },
};

export default function Berry({ variant = "day", mood = "default", size = 120 }) {
  const c = C[variant] || C.day;
  const cls = mood === "thinking" ? "berry-think" : "";
  const rimW = c.rim === "none" ? 0 : 3;
  return (
    <svg className={cls} width={size} height={size} viewBox="0 0 200 200" aria-label="Berry">
      {variant === "night" && (
        <>
          <path d="M 34 52 l 3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="#5EEAD4" opacity=".8" />
          <circle cx="160" cy="34" r="2.6" fill="#5EEAD4" opacity=".7" />
          <circle cx="170" cy="76" r="2.6" fill="#FFC83D" opacity=".7" />
        </>
      )}
      <circle cx="78" cy="40" r="15" fill={c.hat} stroke={c.hatLine} strokeWidth="2" />
      <circle cx="102" cy="34" r="18" fill={c.hat} stroke={c.hatLine} strokeWidth="2" />
      <circle cx="126" cy="40" r="15" fill={c.hat} stroke={c.hatLine} strokeWidth="2" />
      <rect x="66" y="40" width="72" height="15" rx="7.5" fill={c.hat} stroke={c.hatLine} strokeWidth="2" />
      <circle cx="102" cy="106" r="52" fill={c.body} stroke={c.rim} strokeWidth={rimW} />
      {mood === "delighted" ? (
        <>
          <path d="M 74 100 Q 84 88 94 100" stroke={c.smile} strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M 110 100 Q 120 88 130 100" stroke={c.smile} strokeWidth="6" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <rect className="beye" x="76" y="86" width="14" height="22" rx="7" fill={c.eye} />
          <rect className="beye" x="110" y="86" width="14" height="22" rx="7" fill={c.eye} />
          {c.spark !== "none" && (
            <>
              <circle cx="80.5" cy="91.5" r="3.4" fill={c.spark} />
              <circle cx="114.5" cy="91.5" r="3.4" fill={c.spark} />
            </>
          )}
        </>
      )}
      <circle cx="64" cy="116" r="6.5" fill={c.cheek} />
      <circle cx="140" cy="116" r="6.5" fill={c.cheek} />
      <path d="M 88 118 Q 102 130 116 118" stroke={c.smile} strokeWidth="5" fill="none" strokeLinecap="round" />
      <rect x="76" y="134" width="52" height="34" rx="12" fill={c.screen}
        stroke={c.rim} strokeWidth={c.rim === "none" ? 0 : 1.5} />
      <path d="M 92 152 h 20 a 3 3 0 0 1 3 3 v 4 a 6 6 0 0 1 -6 6 h -14 a 6 6 0 0 1 -6 -6 v -4 a 3 3 0 0 1 3 -3 z" fill={c.pot} />
      <path d="M 97 148 q -2 -4 1 -6 M 105 148 q -2 -4 1 -6" stroke={c.pot} strokeWidth="2" fill="none" strokeLinecap="round" />
      <circle cx="44" cy="112" r="11" fill={c.mitt} />
      <circle cx="160" cy="112" r="11" fill={c.mitt} />
      <ellipse cx="102" cy="172" rx="34" ry="7" fill={c.glow} opacity=".4" />
      <ellipse cx="102" cy="170" rx="22" ry="5" fill={c.glow} opacity=".65" />
    </svg>
  );
}

export function BerryAvatar({ variant = "day", mood = "default", size = 38 }) {
  return (
    <span className="avatar" style={{ width: size, height: size }}>
      <Berry variant={variant} mood={mood} size={size * 0.92} />
    </span>
  );
}
