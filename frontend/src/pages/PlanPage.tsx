import { RefreshCw, Repeat2, Search, Wallet } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Spinner, TopBar } from "../components/Chrome";
import Cover from "../components/Cover";
import { useRecipe } from "../components/RecipeSheet";
import Sheet from "../components/Sheet";
import { api, ApiError, soles } from "../lib/api";
import { feel, pulse } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Meal, Plan, RecipeSummary } from "../lib/types";
import { todayIndex } from "./Today";

export default function PlanPage() {
  const { plan, setPlan, toast, openPremium } = useStore();
  const { openRecipe } = useRecipe();
  const [sel, setSel] = useState(todayIndex());
  const [busy, setBusy] = useState(false);
  const [swap, setSwap] = useState<{ day: string; meal: Meal } | null>(null);
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onSwap = (e: Event) => setSwap((e as CustomEvent).detail);
    window.addEventListener("mikuy:swap", onSwap);
    return () => window.removeEventListener("mikuy:swap", onSwap);
  }, []);

  async function regenerate() {
    setBusy(true);
    feel("tap");
    try {
      const r = await api.post<{ plan: Plan }>("/api/plan/generate", { seed: Date.now() % 100000 });
      setPlan(r.plan);
      feel("success");
      toast("Menú nuevo listo");
      pulse(list.current);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) openPremium();
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const day = plan?.days[sel];
  const s = plan?.summary;
  const over = s && s.budget > 0 && s.week_cost > s.budget;
  return (
    <>
      <TopBar
        sub="Tu semana"
        title="Menú"
        right={
          <button className="icon-btn" aria-label="Nuevo menú" onClick={regenerate} disabled={busy}>
            {busy ? <Spinner size={18} /> : <RefreshCw size={18} />}
          </button>
        }
      />
      <div className="page stack">
        <div className="days">
          {(plan?.days ?? []).map((d, i) => (
            <button key={d.date} className={`day ${i === sel ? "on" : ""} ${i === todayIndex() ? "today" : ""}`} onClick={() => { feel("select"); setSel(i); }}>
              <small>{d.day.slice(0, 3)}</small>
              <b>{new Date(d.date + "T12:00").getDate()}</b>
            </button>
          ))}
        </div>

        {s && (
          <div className="card row">
            <Wallet size={20} className="gold" />
            <div className="grow">
              <div className="bold">{soles(s.week_cost)} <span className="muted small">esta semana{s.budget ? ` · presupuesto ${soles(s.budget)}` : ""}</span></div>
              <div className="tiny muted">Promedio {Math.round(s.avg.kcal)} kcal y {Math.round(s.avg.protein)} g de proteína al día</div>
            </div>
            {s.budget > 0 && <span className={`tag ${over ? "red" : "green"}`}>{over ? "+" + soles(s.week_cost - s.budget) : "✓"}</span>}
          </div>
        )}

        <div ref={list} className="stack stagger" key={`${sel}-${plan?.version}`}>
          {day ? (
            day.meals.map((m) => (
              <div key={m.meal} className="card" style={{ padding: 10 }}>
                <button className="meal-card" style={{ background: "none", border: 0, padding: 0 }} onClick={() => { feel("open"); openRecipe(m.recipe.id, { day: day.day, meal: m.meal }); }}>
                  <Cover recipe={m.recipe} />
                  <div className="grow">
                    <div className="kicker">{m.label}</div>
                    <h3>{m.recipe.name}</h3>
                    <div className="small muted">{m.kcal} kcal · {Math.round(m.protein)} g prot. · {soles(m.cost)}</div>
                  </div>
                </button>
                <div className="row" style={{ marginTop: 8 }}>
                  <button className="btn ghost sm grow" onClick={() => { feel("open"); setSwap({ day: day.day, meal: m.meal }); }}>
                    <Repeat2 size={16} /> Cambiar
                  </button>
                  <span className="tag">{m.portion}× porción</span>
                </div>
              </div>
            ))
          ) : plan === null ? (
            <div className="empty">
              <div className="big">🍽️</div>
              <h3>Aún no tienes menú</h3>
              <button className="btn primary" onClick={regenerate}>Crear mi menú</button>
            </div>
          ) : (
            [1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 150 }} />)
          )}
        </div>
      </div>
      <SwapSheet slot={swap} onClose={() => setSwap(null)} />
    </>
  );
}

function SwapSheet({ slot, onClose }: { slot: { day: string; meal: Meal } | null; onClose: () => void }) {
  const { setPlan, toast } = useStore();
  const [q, setQ] = useState("");
  const [items, setItems] = useState<RecipeSummary[] | null>(null);

  useEffect(() => {
    if (!slot) return;
    setItems(null);
    const t = setTimeout(() => {
      api
        .get<{ items: RecipeSummary[] }>(`/api/plan/alternatives?day=${encodeURIComponent(slot.day)}&meal=${slot.meal}&q=${encodeURIComponent(q)}`)
        .then((r) => setItems(r.items))
        .catch((e) => toast(e.message, "error"));
    }, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [slot, q]); // eslint-disable-line react-hooks/exhaustive-deps

  async function choose(id: string) {
    if (!slot) return;
    try {
      const r = await api.post<{ plan: Plan }>("/api/plan/swap", { ...slot, recipe_id: id });
      setPlan(r.plan);
      feel("success");
      toast("Plato cambiado");
      onClose();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  return (
    <Sheet open={!!slot} onClose={() => { setQ(""); onClose(); }} title={slot ? `Cambiar ${slot.meal} del ${slot.day}` : ""}>
      <div className="stack">
        <div className="search">
          <Search size={18} />
          <input className="input" placeholder="Busca: pollo, quinua, barato…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="stack stagger">
          {items?.map((r) => (
            <button key={r.id} className="meal-card" onClick={() => choose(r.id)}>
              <Cover recipe={r} />
              <div className="grow">
                <h3>{r.name}</h3>
                <div className="small muted">{r.kcal} kcal · {r.minutes} min · {soles(r.cost)}/porc.</div>
              </div>
            </button>
          )) ?? [1, 2, 3, 4].map((i) => <div key={i} className="skeleton" style={{ height: 104 }} />)}
          {items && !items.length && <div className="muted center">No encontré opciones con esa búsqueda.</div>}
        </div>
      </div>
    </Sheet>
  );
}
