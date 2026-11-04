import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Spinner } from "../components/Chrome";
import { api } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Me } from "../lib/types";

export default function Welcome() {
  const { setMe, toast } = useStore();
  const [mode, setMode] = useState<"hero" | "login" | "register">("hero");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const me = await api.post<Me>(mode === "login" ? "/api/auth/login" : "/api/auth/register", mode === "login" ? { email, password } : { name, email, password });
      feel("success");
      setMe(me);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  if (mode === "hero") {
    return (
      <div className="hero">
        <div>
          <img className="hero-logo" src="/icons/logo-mark.webp" alt="Mikuy" />
          <h1>
            Come rico, sano
            <br />y <span>dentro de tu presupuesto</span>
          </h1>
          <p>Tu menú semanal peruano, la lista de compras con precios de tu ciudad y Mikuy AI para cambiar lo que quieras.</p>
        </div>
        <div className="floaters" aria-hidden="true">
          {["🥑", "🍋", "🌽", "🐟", "🥔", "🌶️"].map((e, i) => (
            <span key={e} style={{ left: `${8 + i * 16}%`, top: `${(i % 2) * 34}px`, animationDelay: `-${i * 0.9}s` }}>{e}</span>
          ))}
        </div>
        <div className="stack">
          <button className="btn primary block" onClick={() => { feel("tap"); setMode("register"); }}>Empezar gratis</button>
          <button className="btn ghost block" onClick={() => { feel("tap"); setMode("login"); }}>Ya tengo cuenta</button>
        </div>
      </div>
    );
  }

  return (
    <div className="hero" style={{ justifyContent: "flex-start", gap: 24 }}>
      <button className="icon-btn" aria-label="Volver" onClick={() => { feel("close"); setMode("hero"); }}>
        <ArrowLeft size={20} />
      </button>
      <div className="stack" style={{ gap: 6 }}>
        <img src="/icons/logo-mark.webp" alt="" style={{ width: 64 }} />
        <h1 style={{ textAlign: "left", fontSize: 30, margin: "8px 0 0" }}>{mode === "login" ? "Hola de nuevo" : "Crea tu cuenta"}</h1>
        <p style={{ textAlign: "left", margin: 0 }}>{mode === "login" ? "Tu menú y tus compras te esperan." : "Guardamos tu menú, recetas y lista en tu cuenta."}</p>
      </div>
      <form className="stack" onSubmit={submit}>
        {mode === "register" && (
          <div className="field">
            <label htmlFor="name">Nombre</label>
            <input id="name" className="input" autoComplete="given-name" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
          </div>
        )}
        <div className="field">
          <label htmlFor="email">Correo</label>
          <input id="email" className="input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="pw">Contraseña</label>
          <input id="pw" className="input" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "login" ? 1 : 8} />
          {mode === "register" && <span className="tiny muted" style={{ paddingLeft: 4 }}>Mínimo 8 caracteres.</span>}
        </div>
        <button className="btn primary block" disabled={busy} type="submit">
          {busy ? <Spinner /> : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
        </button>
        <button type="button" className="link center" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "¿No tienes cuenta? Créala" : "¿Ya tienes cuenta? Inicia sesión"}
        </button>
      </form>
    </div>
  );
}
