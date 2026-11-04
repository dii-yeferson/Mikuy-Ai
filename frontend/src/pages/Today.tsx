import { ChevronRight, Crown, Sparkles, Wallet } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/Chrome";
import Cover from "../components/Cover";
import { useRecipe } from "../components/RecipeSheet";
import Ring from "../components/Ring";
import { soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";

export const todayIndex = () => (new Date().getDay() + 6) % 7;

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches";
}

export default function Today() {
  const { me, plan, openPremium } = useStore();
  const { openRecipe } = useRecipe();
  const nav = useNavigate();
  const day = plan?.days[todayIndex()];
  const s = plan?.summary;
  const kcal = day?.meals.reduce((a, m) => a + m.kcal, 0) ?? 0;
  const prot = day?.meals.reduce((a, m) => a + m.protein, 0) ?? 0;
  const t = s?.targets;
  const budget = s?.budget ?? 0;
  const over = budget > 0 && (s?.week_cost ?? 0) > budget;
  const dateLabel = new Date().toLocaleDateString("es-PE", { weekday: "long", day: "numeric", month: "short" });

  return (
    <>
      <TopBar sub={`${greeting()}, ${me?.name.split(" ")[0]} · ${dateLabel}`} title="Hoy" />
      <div className="page stack stagger">
        {plan && t ? (
          <div className="card glow">
            <div className="row" style={{ gap: 16 }}>
              <Ring value={kcal} max={t.kcal}>
                <div>
                  <b>{kcal}</b>
                  <span className="tiny muted bold">de {t.kcal} kcal</span>
                </div>
              </Ring>
              <div className="grow stack" style={{ gap: 10 }}>
                <div>
                  <div className="tiny muted bold">PROTEÍNA</div>
                  <div className="bold">{Math.round(prot)} / {t.protein} g</div>
                  <div className="meter" style={{ marginTop: 4 }}><i style={{ width: `${Math.min(100, (prot / t.protein) * 100)}%` }} /></div>
                </div>
                <div>
                  <div className="tiny muted bold">HOY CUESTA</div>
                  <div className="bold gold">{soles(s.days[todayIndex()]?.cost ?? 0)}</div>
                </div>
              </div>
            </div>
            <div className="tiny faint" style={{ marginTop: 10 }}>Meta calculada con Mifflin-St Jeor y tu actividad. IMC {t.bmi}.</div>
          </div>
        ) : (
          <div className="skeleton" style={{ height: 170 }} />
        )}

        {budget > 0 && s && (
          <button className="card" style={{ textAlign: "left" }} onClick={() => { feel("tap"); nav("/compras"); }}>
            <div className="between">
              <div className="row"><Wallet size={18} className="gold" /><span className="bold">Presupuesto de la semana</span></div>
              <span className={`tag ${over ? "red" : "green"}`}>{over ? "Te pasas" : "Dentro"}</span>
            </div>
            <div className="between" style={{ margin: "10px 0 6px" }}>
              <b style={{ fontSize: 22 }}>{soles(s.week_cost)}</b>
              <span className="muted bold">de {soles(budget)}</span>
            </div>
            <div className={`meter ${over ? "over" : ""}`}><i style={{ width: `${Math.min(100, (s.week_cost / budget) * 100)}%` }} /></div>
            <div className="tiny muted" style={{ marginTop: 6 }}>{soles(s.per_person_day)} por persona al día · precios aprox. de tu ciudad</div>
          </button>
        )}

        <div className="section-title">Tus comidas de hoy <small onClick={() => nav("/plan")} style={{ cursor: "pointer" }}>Ver semana</small></div>
        <div className="stack">
          {day?.meals.map((m) => (
            <button key={m.meal} className="meal-card" onClick={() => { feel("open"); openRecipe(m.recipe.id, { day: day.day, meal: m.meal }); }}>
              <Cover recipe={m.recipe} />
              <div className="grow">
                <div className="kicker">{m.label}</div>
                <h3>{m.recipe.name}</h3>
                <div className="small muted">{m.kcal} kcal · {m.recipe.minutes} min · {soles(m.cost)}</div>
              </div>
              <ChevronRight size={18} className="faint" />
            </button>
          )) ?? [1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 104 }} />)}
        </div>

        <button className="card glow" style={{ textAlign: "left" }} onClick={() => { feel("ai"); nav("/ia"); }}>
          <div className="row">
            <div className="avatar" style={{ width: 46, height: 46 }}><Sparkles size={22} /></div>
            <div className="grow">
              <div className="bold">Pregúntale a Mikuy AI</div>
              <div className="small muted">"Cambia la cena de hoy por algo más ligero"</div>
            </div>
            <ChevronRight size={18} className="faint" />
          </div>
        </button>

        {!me?.subscription.premium && (
          <button className="card" style={{ textAlign: "left" }} onClick={() => openPremium()}>
            <div className="row">
              <Crown size={22} className="gold" />
              <div className="grow">
                <div className="bold">Mikuy Premium</div>
                <div className="small muted">IA y voz sin límites, menús ilimitados y plan familiar.</div>
              </div>
              <span className="tag gold">Ver</span>
            </div>
          </button>
        )}
      </div>
    </>
  );
}
