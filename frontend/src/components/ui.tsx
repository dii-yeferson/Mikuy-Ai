import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type ButtonHTMLAttributes,
} from "react";
import {
  ArrowLeft,
  ChevronRight,
  X,
  LoaderCircle,
  NotebookText,
  Plus,
  House,
  MessagesSquare,
} from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { QuickRegister } from "./QuickRegister";

function ThemeLogo({
  className = "",
  alt = "",
}: {
  className?: string;
  alt?: string;
}) {
  return (
    <span className={"theme-logo " + className}>
      <img className="logo-dark" src="/icons/logo-dark.png" alt={alt} />
      <img className="logo-light" src="/icons/logo-light.png" alt={alt} />
    </span>
  );
}
export function Brand({ large = false }: { large?: boolean }) {
  return (
    <div className={"brand " + (large ? "brand-large" : "")}>
      <ThemeLogo />
      <span>Mikuy</span>
    </div>
  );
}
export function Header({
  title,
  back = true,
  right,
}: {
  title: string;
  back?: boolean;
  right?: ReactNode;
}) {
  const navigate = useNavigate();
  return (
    <header className="page-header">
      {back ? (
        <button
          className="icon-button"
          onClick={() =>
            window.history.length > 1 ? navigate(-1) : navigate("/hoy")
          }
          aria-label="Volver"
        >
          <ArrowLeft size={22} />
        </button>
      ) : (
        <ThemeLogo className="header-logo" alt="Mikuy" />
      )}
      <h1>{title}</h1>
      <div className="header-right">{right}</div>
    </header>
  );
}
export function Button({
  children,
  busy = false,
  secondary = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
  secondary?: boolean;
}) {
  return (
    <button
      {...props}
      disabled={props.disabled || busy}
      className={`button ${secondary ? "secondary" : ""} ${className}`}
    >
      {busy && <LoaderCircle className="spin" size={18} />} {children}
    </button>
  );
}
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={"card " + className}>{children}</section>;
}
export function Row({
  children,
  to,
  onClick,
}: {
  children: ReactNode;
  to?: string;
  onClick?: () => void;
}) {
  const inner = (
    <>
      {children}
      <ChevronRight size={17} />
    </>
  );
  return to ? (
    <Link className="row" to={to}>
      {inner}
    </Link>
  ) : (
    <button className="row" onClick={onClick}>
      {inner}
    </button>
  );
}
export function Empty({
  icon = "📋",
  title,
  children,
  action,
}: {
  icon?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="empty">
      <span className="empty-icon" aria-hidden="true">
        {icon}
      </span>
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </section>
  );
}
export function ErrorBox({
  error,
  retry,
}: {
  error: string;
  retry?: () => void;
}) {
  return error ? (
    <div className="error-box" role="alert">
      <p>{error}</p>
      {retry && <button onClick={retry}>Reintentar</button>}
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" /> Cargando…
    </div>
  );
}
export function Sheet({
  title,
  children,
  onClose,
  className = "",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      dialog.close();
      document.body.style.overflow = old;
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={"sheet " + className}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-label={title}
    >
      <div className="sheet-content">
        <header>
          <h2>{title}</h2>
          <button className="icon-button" aria-label="Cerrar" onClick={onClose}>
            <X />
          </button>
        </header>
        {children}
      </div>
    </dialog>
  );
}
export function BottomNav() {
  const [register, setRegister] = useState(false);
  const items = [
    ["/hoy", "Hoy", House],
    ["/menu", "Menú", NotebookText],
    ["/coach", "Mikuy AI", MessagesSquare],
  ] as const;
  return (
    <>
      <div className="floating-navigation">
        <nav className="bottom-nav" aria-label="Navegación principal">
          {items.map(([to, label, Icon]) => (
            <NavLink key={to} to={to}>
              <Icon size={23} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <button
          className="register-fab"
          aria-label="Registrar comida o explorar"
          onClick={() => setRegister(true)}
        >
          <Plus size={28} />
        </button>
      </div>
      {register && <QuickRegister onClose={() => setRegister(false)} />}
    </>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Choice({
  selected,
  icon,
  children,
  onClick,
}: {
  selected: boolean;
  icon?: string;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={"choice " + (selected ? "selected" : "")}
      onClick={onClick}
      aria-pressed={selected}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      <span>{children}</span>
      <span className="radio-mark" aria-hidden="true">
        {selected ? "✓" : ""}
      </span>
    </button>
  );
}

export function Lights({
  traffic,
  conditions,
}: {
  traffic?: Partial<Record<string, "verde" | "amarillo" | "rojo">>;
  conditions: string[];
}) {
  if (!traffic || !conditions.length) return null;
  const short: Record<string, string> = {
    diabetes: "Diabetes",
    prediabetes: "Prediabetes",
    hipertension: "Presión",
    obesidad: "Peso",
  };
  const text = { verde: "Ideal", amarillo: "Con porción", rojo: "Evitar" };
  return (
    <span className="lights">
      {conditions.map((c) => {
        const l = traffic[c] || "verde";
        return (
          <span
            key={c}
            className={"light " + l}
            title={short[c] + ": " + text[l]}
          >
            <i /> {short[c]}: {text[l]}
          </span>
        );
      })}
    </span>
  );
}

/** Foto del plato en /public/recetas/{id}.jpg; si aún no existe, muestra el emoji. */
export function DishImage({
  id,
  emoji,
  name,
  large = false,
}: {
  id: string;
  emoji: string;
  name: string;
  large?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  if (failed)
    return (
      <span
        className={large ? "dish-emoji large" : "meal-emoji"}
        aria-hidden="true"
      >
        {emoji}
      </span>
    );
  return (
    <img
      className={"dish-img " + (large ? "large" : "")}
      src={`/recetas/${id}.jpg`}
      alt={name}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
