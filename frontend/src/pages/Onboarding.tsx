import { ArrowLeft, Minus, Plus } from "lucide-react";
import { useState } from "react";
import { Spinner } from "../components/Chrome";
import { api, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Plan, Profile } from "../lib/types";

type P = Partial<Profile>;
const GOALS = [
  { v: "comer-mejor", em: "🥗", t: "Comer mejor", d: "Más ordenado y nutritivo" },
  { v: "ahorrar", em: "💰", t: "Ahorrar en comida", d: "Gastar menos sin comer peor" },
  { v: "bajar", em: "⚖️", t: "Bajar de peso", d: "Déficit moderado y saciante" },
  { v: "subir", em: "💪", t: "Ganar masa muscular", d: "Más proteína y energía" },
  { v: "mantener", em: "🌿", t: "Mantener mi peso", d: "Equilibrio día a día" },
];
const DIETS = [
  { v: "omnivoro", em: "🍗", t: "Como de todo" },
  { v: "pescetariano", em: "🐟", t: "Pescado, sin carne" },
  { v: "vegetariano", em: "🥚", t: "Vegetariano" },
  { v: "vegano", em: "🌱", t: "Vegano" },
  { v: "sin-gluten", em: "🌾", t: "Sin gluten" },
];
const ALLERGIES = [
  { v: "N", t: "Maní / frutos secos" }, { v: "C", t: "Mariscos" }, { v: "F", t: "Pescado" },
  { v: "D", t: "Lácteos" }, { v: "E", t: "Huevo" }, { v: "G", t: "Gluten" }, { v: "S", t: "Soya" },
];
const CONDITIONS = [
  { v: "diabetes", t: "Diabetes" }, { v: "prediabetes", t: "Prediabetes" }, { v: "hipertension", t: "Presión alta" },
  { v: "colesterol", t: "Colesterol alto" }, { v: "gastritis", t: "Gastritis" }, { v: "embarazo", t: "Embarazo" },
];
const ACTIVITY = [
  { v: "sedentaria", em: "🛋️", t: "Poco activo", d: "Trabajo sentado, casi sin ejercicio" },
  { v: "ligera", em: "🚶", t: "Ligero", d: "Camino o entreno 1–3 días" },
  { v: "moderada", em: "🏃", t: "Activo", d: "Entreno 3–5 días" },
  { v: "intensa", em: "🔥", t: "Muy activo", d: "Entreno fuerte o trabajo físico" },
];

export default function Onboarding() {
  const { me, meta, saveProfile, setPlan, toast } = useStore();
  const [step, setStep] = useState(0);
  const [p, setP] = useState<P>({ ...me!.profile, weekly_budget: me!.profile.weekly_budget || 150 });
  const [busy, setBusy] = useState(false);
  const set = (k: keyof Profile, v: unknown) => { feel("select"); setP((x) => ({ ...x, [k]: v })); };
  const toggle = (k: "allergies" | "conditions", v: string) => {
    feel("select");
    setP((x) => ({ ...x, [k]: (x[k] as string[]).includes(v) ? (x[k] as string[]).filter((i) => i !== v) : [...(x[k] as string[]), v] }));
  };

  const steps = [
    {
      title: `¡Hola, ${me!.name.split(" ")[0]}! ¿Qué quieres lograr?`,
      body: (
        <div className="options">
          {GOALS.map((g) => (
            <button key={g.v} className={`option ${p.goal === g.v ? "on" : ""}`} onClick={() => set("goal", g.v)}>
              <span className="em">{g.em}</span>
              <span>{g.t}<small>{g.d}</small></span>
            </button>
          ))}
        </div>
      ),
    },
    {
      title: "Cuéntame de ti",
      body: (
        <div className="stack">
          <div className="seg">
            {(["mujer", "hombre"] as const).map((s) => (
              <button key={s} className={p.sex === s ? "on" : ""} onClick={() => set("sex", s)}>{s === "mujer" ? "Mujer" : "Hombre"}</button>
            ))}
          </div>
          <div className="options grid2">
            <div className="field"><label>Edad</label><input className="input" type="number" inputMode="numeric" value={p.age} onChange={(e) => setP({ ...p, age: +e.target.value })} /></div>
            <div className="field"><label>Peso (kg)</label><input className="input" type="number" inputMode="decimal" value={p.weight_kg} onChange={(e) => setP({ ...p, weight_kg: +e.target.value })} /></div>
            <div className="field"><label>Talla (cm)</label><input className="input" type="number" inputMode="numeric" value={p.height_cm} onChange={(e) => setP({ ...p, height_cm: +e.target.value })} /></div>
          </div>
          <div className="options">
            {ACTIVITY.map((a) => (
              <button key={a.v} className={`option ${p.activity === a.v ? "on" : ""}`} onClick={() => set("activity", a.v)}>
                <span className="em">{a.em}</span>
                <span>{a.t}<small>{a.d}</small></span>
              </button>
            ))}
          </div>
        </div>
      ),
      ok: () => (p.age ?? 0) >= 14 && (p.weight_kg ?? 0) >= 30 && (p.height_cm ?? 0) >= 120,
    },
    {
      title: "¿Cómo comes?",
      body: (
        <div className="stack">
          <div className="options">
            {DIETS.map((d) => (
              <button key={d.v} className={`option ${p.diet === d.v ? "on" : ""}`} onClick={() => set("diet", d.v)}>
                <span className="em">{d.em}</span>
                <span>{d.t}</span>
              </button>
            ))}
          </div>
          <div className="bold" style={{ marginTop: 6 }}>Alergias</div>
          <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
            {ALLERGIES.map((a) => (
              <button key={a.v} className={`chip ${p.allergies!.includes(a.v) ? "on" : ""}`} onClick={() => toggle("allergies", a.v)}>{a.t}</button>
            ))}
          </div>
          <div className="bold" style={{ marginTop: 6 }}>¿Alguna condición que deba cuidar?</div>
          <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
            {CONDITIONS.map((a) => (
              <button key={a.v} className={`chip ${p.conditions!.includes(a.v) ? "on" : ""}`} onClick={() => toggle("conditions", a.v)}>{a.t}</button>
            ))}
          </div>
        </div>
      ),
    },
    {
      title: "Tu casa y tu presupuesto",
      body: (
        <div className="stack" style={{ gap: 22 }}>
          <div className="card stack center">
            <div className="bold">¿Para cuántas personas cocinas?</div>
            <div className="stepper">
              <button className="icon-btn" aria-label="Menos" onClick={() => set("people", Math.max(1, (p.people ?? 1) - 1))}><Minus /></button>
              <b>{p.people}</b>
              <button className="icon-btn" aria-label="Más" onClick={() => set("people", Math.min(me!.subscription.people_limit, (p.people ?? 1) + 1))}><Plus /></button>
            </div>
            {(p.people ?? 1) >= me!.subscription.people_limit && <div className="tiny muted">¿Cocinas para más? Con Premium hasta 4 y con Familia hasta 12.</div>}
          </div>
          <div className="card stack center">
            <div className="bold">Presupuesto semanal para comida</div>
            <div className="stepper">
              <button className="icon-btn" aria-label="Menos" onClick={() => set("weekly_budget", Math.max(30, (p.weekly_budget ?? 0) - 10))}><Minus /></button>
              <b style={{ fontSize: 36 }}>{soles(p.weekly_budget ?? 0).replace(".00", "")}</b>
              <button className="icon-btn" aria-label="Más" onClick={() => set("weekly_budget", Math.min(2000, (p.weekly_budget ?? 0) + 10))}><Plus /></button>
            </div>
            <input type="range" min={30} max={800} step={5} value={p.weekly_budget} onChange={(e) => setP({ ...p, weekly_budget: +e.target.value })} style={{ accentColor: "#f6c544" }} />
            <div className="small muted">≈ {soles((p.weekly_budget ?? 0) / 7 / (p.people ?? 1))} por persona al día</div>
          </div>
          <div className="field">
            <label htmlFor="city">¿Dónde compras? (para precios aproximados)</label>
            <select id="city" className="input" value={p.city} onChange={(e) => set("city", e.target.value)}>
              {meta?.cities.map((c) => <option key={c.id} value={c.id}>{c.name} · {c.region}</option>)}
            </select>
          </div>
        </div>
      ),
    },
  ];

  const current = steps[step];
  async function next() {
    if (step < steps.length - 1) {
      feel("tap");
      setStep(step + 1);
      window.scrollTo({ top: 0 });
      return;
    }
    setBusy(true);
    try {
      await saveProfile({ ...p, onboarded: false } as Partial<Profile>);
      const r = await api.post<{ plan: Plan }>("/api/plan/generate", {});
      setPlan(r.plan);
      await saveProfile({ onboarded: true });
      feel("celebrate");
      window.scrollTo({ top: 0 });
      toast("¡Tu menú de la semana está listo! 🎉");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hero" style={{ justifyContent: "flex-start", gap: 18 }}>
      <div className="row">
        {step > 0 ? (
          <button className="icon-btn" aria-label="Atrás" onClick={() => { feel("close"); setStep(step - 1); }}><ArrowLeft size={20} /></button>
        ) : (
          <img src="/icons/logo-mark.webp" alt="" style={{ width: 40 }} />
        )}
        <div className="progress grow"><i style={{ width: `${((step + 1) / steps.length) * 100}%` }} /></div>
        <span className="small muted bold">{step + 1}/{steps.length}</span>
      </div>
      <h1 key={step} style={{ textAlign: "left", fontSize: 28, margin: "6px 0 0", animation: "page-in .5s both" }}>{current.title}</h1>
      <div key={`b${step}`} className="grow" style={{ animation: "page-in .5s .05s both" }}>{current.body}</div>
      <button className="btn primary block" disabled={busy || (current.ok ? !current.ok() : false)} onClick={next}>
        {busy ? <><Spinner /> Armando tu menú…</> : step === steps.length - 1 ? "Crear mi menú" : "Continuar"}
      </button>
    </div>
  );
}
