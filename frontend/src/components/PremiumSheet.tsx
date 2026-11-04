import { Check, Copy, Crown, Info, KeyRound } from "lucide-react";
import { useEffect, useState } from "react";
import { api, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Subscription } from "../lib/types";
import { Spinner } from "./Chrome";
import Sheet from "./Sheet";

interface PlanInfo {
  name: string;
  prices: { mensual: number; anual: number };
  members: number;
  features: string[];
}

export default function PremiumSheet() {
  const { premiumOpen, openPremium, me, setMe, toast } = useStore();
  const [plans, setPlans] = useState<Record<string, PlanInfo> | null>(null);
  const [choice, setChoice] = useState<"premium" | "familia">("premium");
  const [period, setPeriod] = useState<"mensual" | "anual">("anual");
  const [step, setStep] = useState<"plans" | "paying" | "code">("plans");
  const [code, setCode] = useState("");
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (premiumOpen && !plans) api.get<{ plans: Record<string, PlanInfo> }>("/api/premium/plans").then((r) => setPlans(r.plans));
    if (premiumOpen) {
      setStep("plans");
      setTyped("");
    }
  }, [premiumOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  async function pay() {
    setBusy(true);
    feel("tap");
    setStep("paying");
    try {
      const r = await api.post<{ code: string }>("/api/premium/checkout", { plan: choice, period });
      await new Promise((res) => setTimeout(res, 1400)); // simula la pasarela
      setCode(r.code);
      setStep("code");
      feel("notify");
    } catch (e) {
      toast((e as Error).message, "error");
      setStep("plans");
    } finally {
      setBusy(false);
    }
  }

  async function redeem() {
    setBusy(true);
    try {
      const sub = await api.post<Subscription>("/api/premium/redeem", { code: typed });
      if (me) setMe({ ...me, subscription: sub });
      feel("celebrate");
      toast(`¡Bienvenido a ${sub.plan_name}! 👑`);
      openPremium(false);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const info = plans?.[choice];
  const price = info?.prices[period] ?? 0;
  const monthly = period === "anual" ? price / 12 : price;
  const sub = me?.subscription;

  return (
    <Sheet open={premiumOpen} onClose={() => openPremium(false)} title="">
      <div className="stack stagger">
        <div className="premium-hero">
          <div className="crown"><Crown size={36} /></div>
          <h2 style={{ margin: "4px 0", fontSize: 26, fontWeight: 1000 }}>Mikuy Premium</h2>
          <p className="muted" style={{ margin: 0 }}>Tu nutricionista y cocinera en el bolsillo.</p>
        </div>

        {sub?.premium ? (
          <div className="card glow stack">
            <div className="bold">Tienes {sub.plan_name} ({sub.period})</div>
            <div className="small muted">Vigente hasta {sub.expires_at ? new Date(sub.expires_at).toLocaleDateString("es-PE") : "—"}.</div>
            {sub.simulated && <div className="notice"><Info size={18} /><span>Activado en modo de prueba: el pago real aún no está configurado.</span></div>}
          </div>
        ) : step === "plans" ? (
          <>
            <div className="seg">
              <button className={period === "mensual" ? "on" : ""} onClick={() => { feel("select"); setPeriod("mensual"); }}>Mensual</button>
              <button className={period === "anual" ? "on" : ""} onClick={() => { feel("select"); setPeriod("anual"); }}>Anual · ahorra 33%</button>
            </div>
            {plans ? (
              (["premium", "familia"] as const).map((k) => (
                <button key={k} className={`plan-card ${choice === k ? "on" : ""}`} onClick={() => { feel("select"); setChoice(k); }}>
                  {k === "familia" && <span className="badge">Para la familia</span>}
                  <div className="between">
                    <div className="bold" style={{ fontSize: 17 }}>{plans[k].name}</div>
                    <div style={{ textAlign: "right" }}>
                      <div className="bold gold" style={{ fontSize: 18 }}>{soles(plans[k].prices[period])}</div>
                      <div className="tiny muted">{period === "anual" ? `${soles(plans[k].prices.anual / 12)} al mes` : "al mes"}</div>
                    </div>
                  </div>
                  <div className="stack" style={{ gap: 6, marginTop: 10 }}>
                    {plans[k].features.map((f) => (
                      <div key={f} className="row small"><Check size={16} className="gold" /> {f}</div>
                    ))}
                  </div>
                </button>
              ))
            ) : (
              <div className="skeleton" style={{ height: 260 }} />
            )}
            <button className="btn primary block" disabled={!info || busy} onClick={pay}>
              Pagar {soles(price)} {period === "anual" && <span className="small">({soles(monthly)}/mes)</span>}
            </button>
            <div className="notice"><Info size={18} /><span>Modo de prueba: el pago real (tarjeta, Yape) aún no está configurado. Al pagar, Mikuy te dará un código para activar tu plan.</span></div>
          </>
        ) : step === "paying" ? (
          <div className="card center stack" style={{ padding: 30, alignItems: "center" }}>
            <Spinner size={34} />
            <div className="bold">Procesando pago de prueba…</div>
            <div className="small muted">{info?.name} · {period} · {soles(price)}</div>
          </div>
        ) : (
          <div className="stack">
            <div className="card glow stack">
              <div className="bold">Pago de prueba aprobado ✅</div>
              <div className="small muted">Este es tu código de activación (vence en 30 minutos). Escríbelo abajo para activar {info?.name}.</div>
              <div className="code-box">{code}</div>
              <button className="btn ghost sm" onClick={() => { navigator.clipboard?.writeText(code); feel("success"); toast("Código copiado"); }}>
                <Copy size={16} /> Copiar código
              </button>
            </div>
            <div className="field">
              <label htmlFor="code">Código de activación</label>
              <input id="code" className="input" value={typed} placeholder="MIKUY-XXXX-XXXX" autoCapitalize="characters" onChange={(e) => setTyped(e.target.value.toUpperCase())} />
            </div>
            <button className="btn primary block" disabled={typed.length < 10 || busy} onClick={redeem}>
              <KeyRound size={18} /> Activar mi plan
            </button>
            <div className="notice"><Info size={18} /><span>Falta la configuración real de pago. Cuando se conecte, este paso será automático.</span></div>
          </div>
        )}
      </div>
    </Sheet>
  );
}
