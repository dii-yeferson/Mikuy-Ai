import { BookMarked, Crown, ExternalLink, LogOut, Moon, Trash2, Volume2, Vibrate, Speech } from "lucide-react";
import { useState } from "react";
import { TopBar } from "../components/Chrome";
import Sheet from "../components/Sheet";
import { api, ApiError, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Profile } from "../lib/types";

const GOAL: Record<string, string> = { "comer-mejor": "Comer mejor", ahorrar: "Ahorrar", bajar: "Bajar de peso", subir: "Ganar músculo", mantener: "Mantener" };

export default function Settings() {
  const { me, meta, saveProfile, setMe, openPremium, toast, setPlan } = useStore();
  const [sources, setSources] = useState(false);
  const [confirm, setConfirm] = useState(false);
  if (!me) return null;
  const p = me.profile;
  const sub = me.subscription;

  async function change(k: keyof Profile, v: unknown, regen = false) {
    try {
      await saveProfile({ [k]: v } as Partial<Profile>);
      if (regen) {
        const r = await api.post<{ plan: import("../lib/types").Plan }>("/api/plan/generate", {}).catch(() => null);
        if (r) setPlan(r.plan);
      }
      feel("success");
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) openPremium();
      toast((e as Error).message, "error");
    }
  }

  const sw = (k: "sounds" | "haptics" | "voice_reply" | "snacks", label: string, Icon: typeof Volume2, regen = false) => (
    <button className="list-row" onClick={() => { feel(p[k] ? "toggleOff" : "toggleOn"); change(k, !p[k], regen); }}>
      <span className="ico"><Icon size={18} /></span>
      <span className="grow bold">{label}</span>
      <span className={`switch ${p[k] ? "on" : ""}`} />
    </button>
  );

  return (
    <>
      <TopBar sub={me.email} title={me.name} />
      <div className="page stack stagger">
        <button className={`card ${sub.premium ? "glow" : ""}`} style={{ textAlign: "left" }} onClick={() => openPremium()}>
          <div className="row">
            <Crown className="gold" />
            <div className="grow">
              <div className="bold">{sub.plan_name}</div>
              <div className="small muted">
                {sub.premium ? `Vigente hasta ${new Date(sub.expires_at!).toLocaleDateString("es-PE")}${sub.simulated ? " · modo de prueba" : ""}` : "Mejora a Premium: IA y voz sin límites"}
              </div>
            </div>
            <span className="tag gold">{sub.premium ? "Ver" : "Mejorar"}</span>
          </div>
        </button>

        <div className="section-title">Mi plan de alimentación</div>
        <div className="list">
          <div className="list-row"><span className="grow bold">Objetivo</span>
            <select className="input" style={{ width: 170, height: 40 }} value={p.goal} onChange={(e) => change("goal", e.target.value, true)}>
              {Object.entries(GOAL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="list-row"><span className="grow bold">Presupuesto semanal</span>
            <input className="input" style={{ width: 120, height: 40 }} type="number" inputMode="numeric" defaultValue={p.weekly_budget} onBlur={(e) => +e.target.value !== p.weekly_budget && change("weekly_budget", +e.target.value, true)} />
          </div>
          <div className="list-row"><span className="grow bold">Personas</span>
            <input className="input" style={{ width: 90, height: 40 }} type="number" min={1} max={12} defaultValue={p.people} onBlur={(e) => +e.target.value !== p.people && change("people", Math.max(1, Math.min(12, +e.target.value)), true)} />
          </div>
          <div className="list-row"><span className="grow bold">Ciudad</span>
            <select className="input" style={{ width: 170, height: 40 }} value={p.city} onChange={(e) => change("city", e.target.value)}>
              {meta?.cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="list-row"><span className="grow bold">Alimentación</span>
            <select className="input" style={{ width: 170, height: 40 }} value={p.diet} onChange={(e) => change("diet", e.target.value, true)}>
              <option value="omnivoro">De todo</option><option value="pescetariano">Pescetariana</option><option value="vegetariano">Vegetariana</option><option value="vegano">Vegana</option><option value="sin-gluten">Sin gluten</option>
            </select>
          </div>
          <div className="list-row"><span className="grow bold">Tiempo máx. por receta</span>
            <select className="input" style={{ width: 130, height: 40 }} value={p.max_minutes} onChange={(e) => change("max_minutes", +e.target.value, true)}>
              <option value={0}>Sin límite</option><option value={20}>20 min</option><option value={30}>30 min</option><option value={45}>45 min</option><option value={60}>1 hora</option>
            </select>
          </div>
          {sw("snacks", "Incluir snack diario", BookMarked, true)}
        </div>
        {p.excluded.length > 0 && (
          <div className="card">
            <div className="bold" style={{ marginBottom: 8 }}>No me gusta</div>
            <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
              {p.excluded.map((id) => (
                <button key={id} className="chip on" onClick={() => change("excluded", p.excluded.filter((x) => x !== id), true)}>
                  {meta?.ingredients.find((i) => i.id === id)?.name ?? id} ✕
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="section-title">Experiencia</div>
        <div className="list">
          {sw("sounds", "Sonidos", Volume2)}
          {sw("haptics", "Vibración", Vibrate)}
          {sw("voice_reply", "Mikuy AI responde en voz alta", Speech)}
          <div className="list-row">
            <span className="ico"><Moon size={18} /></span>
            <span className="grow bold">Apariencia</span>
            <div className="seg" style={{ width: 190 }}>
              {(["auto", "claro", "oscuro"] as const).map((t) => (
                <button key={t} className={p.theme === t ? "on" : ""} onClick={() => { feel("select"); change("theme", t); }} style={{ fontSize: 13 }}>{t}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="section-title">Información</div>
        <div className="list">
          <button className="list-row" onClick={() => setSources(true)}>
            <span className="ico"><BookMarked size={18} /></span>
            <span className="grow bold">Fuentes de nutrición y precios</span>
          </button>
          <button className="list-row" onClick={async () => { feel("tap"); await api.post("/api/auth/logout"); setMe(null); }}>
            <span className="ico"><LogOut size={18} /></span>
            <span className="grow bold">Cerrar sesión</span>
          </button>
          <button className="list-row" onClick={() => setConfirm(true)} style={{ color: "var(--red)" }}>
            <span className="ico" style={{ background: "rgba(255,107,94,.12)", color: "var(--red)" }}><Trash2 size={18} /></span>
            <span className="grow bold">Eliminar mi cuenta</span>
          </button>
        </div>
        <div className="tiny faint center" style={{ padding: "10px 0 20px" }}>Mikuy 2.0 · {meta?.recipes} recetas · Presupuesto ≈ {soles((p.weekly_budget || 0) / 7 / Math.max(1, p.people))} por persona al día</div>
      </div>

      <Sheet open={sources} onClose={() => setSources(false)} title="Fuentes">
        <div className="stack">
          <p className="small muted" style={{ margin: 0 }}>{meta?.nutrition_note} {meta?.price_note}</p>
          {(["nutricion", "precios"] as const).map((topic) => (
            <div key={topic}>
              <div className="section-title" style={{ marginTop: 6 }}>{topic === "nutricion" ? "Nutrición" : "Precios"}</div>
              <div className="list">
                {meta?.sources.filter((s) => s.topic === topic).map((s) => (
                  <a key={s.id} className="list-row" href={s.url} target="_blank" rel="noopener noreferrer" style={{ color: "inherit" }}>
                    <div className="grow">
                      <div className="bold small">{s.title}</div>
                      <div className="tiny muted">{s.publisher} · {s.use}</div>
                    </div>
                    <ExternalLink size={16} className="gold" />
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Sheet>

      <Sheet open={confirm} onClose={() => setConfirm(false)} title="¿Eliminar tu cuenta?">
        <div className="stack">
          <p className="muted" style={{ margin: 0 }}>Se borrarán tu perfil, menús, compras y conversaciones. No se puede deshacer.</p>
          <button className="btn danger block" onClick={async () => { feel("remove"); await api.del("/api/auth/me"); setMe(null); }}>Sí, eliminar todo</button>
          <button className="btn ghost block" onClick={() => setConfirm(false)}>Cancelar</button>
        </div>
      </Sheet>
    </>
  );
}
