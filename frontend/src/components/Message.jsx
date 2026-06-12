import { BerryAvatar } from "../berry.jsx";
import { DishCards, RecipeCard } from "./DishCards.jsx";

export default function Message({ m, variant, onChip, onPickDish }) {
  if (m.role === "user") {
    return (
      <div className="bubble-me">
        {m.text}
        {m.image && <img src={m.image.dataUrl} alt="attached" />}
      </div>
    );
  }
  const r = m.reply;
  const mood = r.dishes?.length || r.recipe ? "delighted" : "default";
  return (
    <>
      <div className="row">
        <BerryAvatar variant={variant} mood={mood} />
        <div className="bubble-bot">
          {r.message}
          {r.goal && <div className="goal">🎯 {r.goal}</div>}
          {r.sources?.length > 0 && (
            <div>
              {r.sources.map((s, i) => (
                <a key={i} className="srclink" href={s.url} target="_blank" rel="noreferrer">
                  🔗 {s.title || s.url} ↗
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
      {r.dishes?.length > 0 && <DishCards dishes={r.dishes} onPick={onPickDish} />}
      {r.recipe && <RecipeCard recipe={r.recipe} />}
      {r.chips?.length > 0 && (
        <div className="chips">
          {r.chips.map((c, i) => (
            <button key={i} className="chip" onClick={() => onChip(c)}>{c}</button>
          ))}
        </div>
      )}
    </>
  );
}
