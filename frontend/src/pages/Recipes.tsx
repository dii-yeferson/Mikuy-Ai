import { Heart, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { TopBar } from "../components/Chrome";
import Cover from "../components/Cover";
import { useRecipe } from "../components/RecipeSheet";
import { api, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { RecipeSummary } from "../lib/types";

const FILTERS = [
  { k: "", t: "Todas" },
  { k: "fav", t: "❤️ Favoritas" },
  { k: "meal:desayuno", t: "Desayunos" },
  { k: "meal:almuerzo", t: "Almuerzos" },
  { k: "meal:cena", t: "Cenas" },
  { k: "meal:snack", t: "Snacks y postres" },
  { k: "tag:rapido", t: "⚡ Rápidas" },
  { k: "tag:economico", t: "💰 Económicas" },
  { k: "tag:criollo", t: "Criollas" },
  { k: "tag:andino", t: "Andinas" },
  { k: "tag:marino", t: "Marinas" },
  { k: "tag:amazonico", t: "Amazónicas" },
  { k: "tag:vegetariano", t: "Vegetarianas" },
  { k: "tag:chifa", t: "Chifa" },
];

export default function Recipes() {
  const { me, meta } = useStore();
  const { openRecipe } = useRecipe();
  const [q, setQ] = useState("");
  const [f, setF] = useState("");
  const [items, setItems] = useState<RecipeSummary[] | null>(null);
  const [limit, setLimit] = useState(40);

  useEffect(() => {
    const params = new URLSearchParams({ q });
    if (f.startsWith("meal:")) params.set("meal", f.slice(5));
    if (f.startsWith("tag:")) params.set("tag", f.slice(4));
    const t = setTimeout(() => {
      api.get<{ items: RecipeSummary[] }>(`/api/recipes?${params}`).then((r) => { setItems(r.items); setLimit(40); });
    }, q ? 220 : 0);
    return () => clearTimeout(t);
  }, [q, f]);

  const favs = me?.profile.favorites ?? [];
  const shown = (f === "fav" ? items?.filter((r) => favs.includes(r.id)) : items) ?? null;

  return (
    <>
      <TopBar sub={`${meta?.recipes ?? 300}+ recetas peruanas`} title="Recetario" />
      <div className="page stack">
        <div className="search">
          <Search size={18} />
          <input className="input" placeholder="Busca lomo, quinua, cebiche…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="chips">
          {FILTERS.map((x) => (
            <button key={x.k} className={`chip ${f === x.k ? "on" : ""}`} onClick={() => { feel("select"); setF(x.k); }}>{x.t}</button>
          ))}
        </div>
        <div className="small muted">{shown ? `${shown.length} recetas compatibles con tu perfil` : "Cargando…"}</div>
        <div className="recipe-grid stagger" key={f + q}>
          {shown
            ? shown.slice(0, limit).map((r) => (
                <button key={r.id} className="recipe-tile" onClick={() => { feel("open"); openRecipe(r.id); }}>
                  <div style={{ position: "relative" }}>
                    <Cover recipe={r} />
                    {favs.includes(r.id) && <span className="fav-dot"><Heart size={15} fill="currentColor" /></span>}
                  </div>
                  <h3>{r.name}</h3>
                  <div className="tiny muted bold">{r.kcal} kcal · {r.minutes} min · {soles(r.cost)}</div>
                </button>
              ))
            : Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton" style={{ aspectRatio: "4/4.4" }} />)}
        </div>
        {shown && shown.length > limit && (
          <button className="btn ghost block" onClick={() => setLimit(limit + 40)}>Ver más recetas</button>
        )}
        {shown && !shown.length && (
          <div className="empty"><div className="big">🔍</div><div className="muted">No encontré recetas con eso.</div></div>
        )}
      </div>
    </>
  );
}
