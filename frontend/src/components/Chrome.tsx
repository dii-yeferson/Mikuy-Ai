import { BookOpen, CalendarDays, House, ShoppingBasket, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";

export function Dock() {
  const tab = () => feel("select");
  return (
    <nav className="dock glass" aria-label="Navegación principal">
      <NavLink to="/" end onClick={tab}>
        <House size={22} />
        Hoy
      </NavLink>
      <NavLink to="/plan" onClick={tab}>
        <CalendarDays size={22} />
        Menú
      </NavLink>
      <NavLink to="/ia" className="ai-btn" aria-label="Mikuy AI" onClick={() => feel("ai")}>
        <Sparkles size={28} />
      </NavLink>
      <NavLink to="/compras" onClick={tab}>
        <ShoppingBasket size={22} />
        Compras
      </NavLink>
      <NavLink to="/recetas" onClick={tab}>
        <BookOpen size={22} />
        Recetas
      </NavLink>
    </nav>
  );
}

export function TopBar({ title, sub, right }: { title: ReactNode; sub?: ReactNode; right?: ReactNode }) {
  const { me } = useStore();
  const nav = useNavigate();
  return (
    <header className="topbar">
      <div className="grow">
        {sub && <div className="sub">{sub}</div>}
        <h1>{title}</h1>
      </div>
      {right}
      <button className="avatar" aria-label="Ajustes y cuenta" onClick={() => { feel("tap"); nav("/ajustes"); }}>
        {(me?.name ?? "M").trim().charAt(0).toUpperCase()}
      </button>
    </header>
  );
}

export function Toasts() {
  const { toasts } = useStore();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast glass ${t.tone}`}>
          <span className="dot" />
          <span>{t.text}</span>
          {t.action && <button onClick={t.action.run}>{t.action.label}</button>}
        </div>
      ))}
    </div>
  );
}

export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg className="spin" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
