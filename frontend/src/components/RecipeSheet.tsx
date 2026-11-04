import { CalendarPlus, Clock, Flame, Heart, Minus, Plus, Repeat2, TriangleAlert, Wallet } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Meal, Plan, RecipeDetail } from "../lib/types";
import Cover from "./Cover";
import Sheet from "./Sheet";

interface Slot {
  day: string;
  meal: Meal;
}
interface Ctx {
  openRecipe: (id: string, slot?: Slot) => void;
}
const RecipeCtx = createContext<Ctx>({ openRecipe: () => {} });
export const useRecipe = () => useContext(RecipeCtx);

const DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];

export function RecipeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ id: string; slot?: Slot } | null>(null);
  const openRecipe = useCallback((id: string, slot?: Slot) => setState({ id, slot }), []);
  return (
    <RecipeCtx.Provider value={{ openRecipe }}>
      {children}
      <RecipeSheet state={state} onClose={() => setState(null)} />
    </RecipeCtx.Provider>
  );
}

function RecipeSheet({ state, onClose }: { state: { id: string; slot?: Slot } | null; onClose: () => void }) {
  const { me, setMe, plan, setPlan, toast, meta } = useStore();
  const [data, setData] = useState<RecipeDetail | null>(null);
  const [portion, setPortion] = useState(1);
  const [adding, setAdding] = useState(false);
  const [day, setDay] = useState(DAYS[(new Date().getDay() + 6) % 7]);
  const nav = useNavigate();
  const open = !!state;

  useEffect(() => {
    if (!state) return;
    setData(null);
    setAdding(false);
    const slotMeal = state.slot && plan?.days.find((d) => d.day === state.slot!.day)?.meals.find((m) => m.meal === state.slot!.meal);
    const p = slotMeal?.portion ?? 1;
    setPortion(p * (me?.profile.people ?? 1));
    api.get<RecipeDetail>(`/api/recipes/${state.id}?portion=${p * (me?.profile.people ?? 1)}`).then(setData).catch((e) => toast(e.message, "error"));
  }, [state?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function changePortion(next: number) {
    if (!data || next < 0.5 || next > 12) return;
    feel("select");
    setPortion(next);
    setData(await api.get<RecipeDetail>(`/api/recipes/${data.id}?portion=${next}`));
  }

  async function toggleFav() {
    if (!data || !me) return;
    const fav = me.profile.favorites.includes(data.id);
    feel(fav ? "toggleOff" : "toggleOn");
    await (fav ? api.del(`/api/favorites/${data.id}`) : api.put(`/api/favorites/${data.id}`));
    const favorites = fav ? me.profile.favorites.filter((f) => f !== data.id) : [...me.profile.favorites, data.id];
    setMe({ ...me, profile: { ...me.profile, favorites } });
    toast(fav ? "Quitada de favoritas" : "Guardada en favoritas ❤️");
  }

  async function addToPlan(targetDay: string) {
    if (!data) return;
    try {
      if (!plan) {
        toast("Primero crea tu menú de la semana.", "info");
        return;
      }
      const r = await api.post<{ plan: Plan }>("/api/plan/swap", { day: targetDay, meal: data.meal, recipe_id: data.id });
      setPlan(r.plan);
      feel("success");
      toast(`Listo: ${data.name} el ${targetDay}`);
      onClose();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  const fav = data && me?.profile.favorites.includes(data.id);
  const n = data?.nutrition;
  const people = me?.profile.people ?? 1;
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={data ? <span className="ellipsis" style={{ display: "block", maxWidth: 240 }}>{data.name}</span> : "Receta"}
      actions={
        data && (
          <button className="icon-btn" aria-label="Favorita" onClick={toggleFav} style={fav ? { color: "#ff6b8a" } : undefined}>
            <Heart size={20} fill={fav ? "currentColor" : "none"} />
          </button>
        )
      }
    >
      {!data ? (
        <div className="stack">
          <div className="skeleton" style={{ height: 220 }} />
          <div className="skeleton" style={{ height: 80 }} />
          <div className="skeleton" style={{ height: 160 }} />
        </div>
      ) : (
        <div className="stack stagger">
          <Cover recipe={data} size={96} />
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            <span className="tag gold"><Clock size={13} /> {data.minutes} min</span>
            <span className="tag"><Flame size={13} /> {Math.round(n!.kcal / portion)} kcal/porción</span>
            <span className="tag"><Wallet size={13} /> {soles(data.cost / portion)} por porción</span>
            {data.region !== "Perú" && <span className="tag">{data.region}</span>}
            {data.diet.map((d) => <span key={d} className="tag green">{d}</span>)}
          </div>

          {data.warnings.map((w) => (
            <div key={w} className="notice warn"><TriangleAlert size={18} /> <span>{w}</span></div>
          ))}

          <div className="card">
            <div className="between">
              <div>
                <div className="bold">Porciones</div>
                <div className="small muted">{people > 1 ? `Tu familia: ${people} personas` : "Ajusta y todo se recalcula"}</div>
              </div>
              <div className="row">
                <button className="icon-btn" aria-label="Menos" onClick={() => changePortion(portion - 0.5)}><Minus size={18} /></button>
                <b style={{ minWidth: 36, textAlign: "center", fontSize: 20 }}>{portion}</b>
                <button className="icon-btn" aria-label="Más" onClick={() => changePortion(portion + 0.5)}><Plus size={18} /></button>
              </div>
            </div>
          </div>

          <div className="macro">
            <div><div className="tiny muted bold">Proteína</div><b>{Math.round(n!.protein / portion)} g</b></div>
            <div><div className="tiny muted bold">Carbos</div><b>{Math.round(n!.carbs / portion)} g</b></div>
            <div><div className="tiny muted bold">Grasa</div><b>{Math.round(n!.fat / portion)} g</b></div>
            <div><div className="tiny muted bold">Fibra</div><b>{Math.round(n!.fiber / portion)} g</b></div>
            <div><div className="tiny muted bold">Sodio</div><b>{Math.round(n!.sodium / portion)} mg</b></div>
            <div><div className="tiny muted bold">Total</div><b className="gold">{soles(data.cost)}</b></div>
          </div>

          <div>
            <div className="section-title" style={{ marginTop: 6 }}>Ingredientes <small>{portion} porc.</small></div>
            <div className="list">
              {data.ingredients.map((i) => (
                <div key={i.id} className="list-row">
                  <div className="grow">
                    <div className="bold">{i.name}</div>
                    <div className="tiny muted">aprox. {soles(i.unit_price)}/{i.price_unit}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="bold">{i.qty} {i.unit}</div>
                    <div className="tiny muted">{soles(i.cost)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="section-title" style={{ marginTop: 6 }}>Preparación</div>
            <div className="stack">
              {data.steps.map((s, i) => (
                <div key={i} className="row" style={{ alignItems: "flex-start" }}>
                  <span className="avatar" style={{ width: 30, height: 30, fontSize: 14, flex: "none" }}>{i + 1}</span>
                  <p style={{ margin: "4px 0 0" }}>{s}</p>
                </div>
              ))}
            </div>
          </div>

          {data.allergens.length > 0 && <div className="small muted">Contiene: {data.allergens.join(", ")}.</div>}
          <div className="tiny faint">{meta?.nutrition_note} {meta?.price_note}</div>

          {state?.slot ? (
            <button className="btn ghost block" onClick={() => { const slot = state.slot; onClose(); nav("/plan"); setTimeout(() => window.dispatchEvent(new CustomEvent("mikuy:swap", { detail: slot })), 350); }}>
              <Repeat2 size={18} /> Cambiar este plato
            </button>
          ) : adding ? (
            <div className="card stack">
              <div className="bold">¿Qué día va este {data.meal}?</div>
              <div className="chips">
                {DAYS.map((d) => (
                  <button key={d} className={`chip ${d === day ? "on" : ""}`} onClick={() => { feel("select"); setDay(d); }}>{d}</button>
                ))}
              </div>
              <button className="btn primary block" onClick={() => addToPlan(day)}>Poner en mi menú</button>
            </div>
          ) : (
            <button className="btn primary block" onClick={() => { feel("tap"); setAdding(true); }}>
              <CalendarPlus size={18} /> Agregar a mi menú
            </button>
          )}
        </div>
      )}
    </Sheet>
  );
}
