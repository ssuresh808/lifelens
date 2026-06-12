export function DishCards({ dishes, onPick }) {
  return dishes.map((d) => (
    <button key={d.id || d.name} className="dish" onClick={() => onPick(d)}>
      <span className="ct">
        {[d.cuisine, d.minutes ? `${d.minutes} MIN` : "", d.serves ? `SERVES ${d.serves}` : "", d.difficulty]
          .filter(Boolean).join(" · ").toUpperCase()}
      </span>
      <b>{d.name}</b>
      {d.have?.length > 0 && <span className="meta">✓ uses: {d.have.join(", ")}</span>}
      {d.nice_to_add?.length > 0 && <span className="meta"> · nice to add: {d.nice_to_add.join(", ")}</span>}
    </button>
  ));
}

export function RecipeCard({ recipe }) {
  return (
    <div className="recipe">
      <h3>{recipe.name}</h3>
      <div style={{ color: "var(--muted)", fontSize: 12.5 }}>
        {[recipe.cuisine, recipe.minutes ? `${recipe.minutes} min` : "", recipe.serves ? `serves ${recipe.serves}` : ""]
          .filter(Boolean).join(" · ")}
      </div>
      <ul>{recipe.ingredients.map((i, k) => <li key={k}><b>{i.amount}</b> {i.item}</li>)}</ul>
      <ol>{recipe.steps.map((s, k) => <li key={k}>{s}</li>)}</ol>
    </div>
  );
}
