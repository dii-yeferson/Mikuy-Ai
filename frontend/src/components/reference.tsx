import { type ReactNode, useState } from "react";
import {
  ChevronRight,
  Check,
  GripHorizontal,
  Minus,
  Plus,
  Globe,
  BookOpen,
  Moon,
  Vibrate,
  Apple,
  Droplet,
  Weight,
  Ruler,
  Zap,
} from "lucide-react";
import { Sheet, Button, ErrorBox } from "./ui";

const settingIcons: Record<string, typeof Globe> = {
  "Idioma de Interfaz": Globe,
  "Idioma de Alimentos": BookOpen,
  "País de Alimentos": Globe,
  Apariencia: Moon,
  "Vibración de Botones": Vibrate,
  "Peso de Alimentos": Apple,
  "Volumen de Líquidos": Droplet,
  "Peso Corporal": Weight,
  Estatura: Ruler,
  "Unidad de Energía": Zap,
};

export function Toggle({
  label,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-label={label}
      aria-checked={value}
      disabled={disabled}
      className={"ref-switch " + (value ? "on" : "")}
      onClick={() => onChange(!value)}
    >
      <span />
    </button>
  );
}
export function SettingRow({
  label,
  value,
  onClick,
  children,
  icon,
}: {
  label: string;
  value?: ReactNode;
  onClick?: () => void;
  children?: ReactNode;
  icon?: ReactNode;
}) {
  const Icon = settingIcons[label];
  const content = (
    <>
      <span className="ref-row-label">
        {icon || (Icon && <Icon size={18} aria-hidden="true" />)}
        {label}
      </span>
      <span className="ref-row-value">{value}</span>
      {children || <ChevronRight size={17} />}
    </>
  );
  return onClick ? (
    <button className="ref-row" onClick={onClick}>
      {content}
    </button>
  ) : (
    <div className="ref-row">{content}</div>
  );
}
export function OptionRow({
  label,
  selected,
  onClick,
  icon,
  description,
  trailing,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
  icon?: ReactNode;
  description?: string;
  trailing?: string;
}) {
  return (
    <button
      type="button"
      className={"ref-option " + (selected ? "selected" : "")}
      onClick={onClick}
      aria-pressed={selected}
    >
      {icon && <span className="ref-option-icon">{icon}</span>}
      <span className="ref-option-copy">
        {label}
        {description && <small>{description}</small>}
      </span>
      {trailing ? (
        <small>{trailing}</small>
      ) : (
        <span className="ref-selection">
          {selected ? <Check size={13} /> : null}
        </span>
      )}
    </button>
  );
}
export function Picker({
  title,
  value,
  choices,
  onSave,
  onClose,
  unitChoices,
}: {
  title: string;
  value: string | number;
  choices: (string | number)[];
  onSave: (v: string | number) => void | Promise<void>;
  onClose: () => void;
  unitChoices?: string[];
}) {
  const [selected, setSelected] = useState(value),
    [unit, setUnit] = useState(unitChoices?.[0] || "");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <Sheet title={title} onClose={onClose}>
      {unitChoices && (
        <div className="segments compact">
          {unitChoices.map((u) => (
            <button
              key={u}
              className={unit === u ? "active" : ""}
              onClick={() => setUnit(u)}
            >
              {u}
            </button>
          ))}
        </div>
      )}
      <div className="wheel-picker" role="listbox" aria-label={title}>
        {choices.map((v) => (
          <button
            type="button"
            key={v}
            role="option"
            aria-selected={selected === v}
            className={selected === v ? "chosen" : ""}
            ref={(el) => {
              if (selected === v && el?.parentElement)
                el.parentElement.scrollTop =
                  el.offsetTop -
                  el.parentElement.offsetTop -
                  el.parentElement.clientHeight / 2 +
                  el.clientHeight / 2;
            }}
            onClick={() => setSelected(v)}
          >
            {v}{" "}
            {unit === "lbs" && typeof v === "number"
              ? `(${(v * 2.20462).toFixed(1)} lb)`
              : unit === "ft/in" && typeof v === "number"
                ? `(${Math.floor(v / 30.48)}′ ${Math.round(v / 2.54) % 12}″)`
                : ""}
          </button>
        ))}
      </div>
      <ErrorBox error={error} />
      <Button
        disabled={!choices.includes(selected)}
        busy={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await onSave(selected);
            onClose();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        Aceptar
      </Button>
    </Sheet>
  );
}
export function Gauge({
  value,
  target,
  onEdit,
  onMore,
}: {
  value: number;
  target: number | null;
  onEdit?: () => void;
  onMore?: () => void;
}) {
  const percent = target ? Math.min(value / target, 1) : 0;
  return (
    <div className="ref-gauge">
      <div className="between">
        {onEdit ? (
          <button
            aria-label="Editar nutrientes"
            className="icon-button"
            onClick={onEdit}
          >
            ✎
          </button>
        ) : (
          <span />
        )}
        <span>kcal ›</span>
        {onMore ? (
          <button
            aria-label="Opciones del día"
            className="icon-button"
            onClick={onMore}
          >
            •••
          </button>
        ) : (
          <span />
        )}
      </div>
      <div className="ref-gauge-number">
        <span>{Math.round(value).toLocaleString("es-PE")}</span> /{" "}
        {target?.toLocaleString("es-PE") || "—"}
      </div>
      <svg viewBox="0 0 300 50" aria-hidden="true">
        <path
          d="M8 40 Q150 0 292 40"
          fill="none"
          stroke="#363934"
          strokeWidth="5"
          strokeLinecap="round"
        />
        {percent > 0 && (
          <path
            d="M8 40 Q150 0 292 40"
            fill="none"
            stroke="var(--leaf)"
            strokeWidth="5"
            strokeLinecap="round"
            pathLength="100"
            strokeDasharray={`${percent * 100} 100`}
          />
        )}
        <path d="M113 21v8m74-8v8" stroke="#6b6b66" strokeWidth="3" />
      </svg>
      {target && (
        <div className="gauge-range">
          <span>{Math.round(target * 0.9).toLocaleString("es-PE")}</span>
          <span>{Math.round(target * 1.1).toLocaleString("es-PE")}</span>
        </div>
      )}
    </div>
  );
}
export function MacroRow({
  values,
  target,
  percentages,
}: {
  values: number[];
  target: number | null;
  percentages: number[];
}) {
  return (
    <div className="ref-macros">
      {["Proteínas", "Carbs", "Grasas"].map((label, i) => {
        const grams = target
          ? Math.round((target * percentages[i]) / 100 / (i === 2 ? 9 : 4))
          : null;
        return (
          <div key={label}>
            <span>{label} ›</span>
            <strong>
              <b>{Math.round(values[i])}</b> / {grams ?? "—"}g
            </strong>
            <i>
              <em
                style={{
                  width: grams
                    ? `${Math.min((values[i] / grams) * 100, 100)}%`
                    : "0%",
                }}
              />
            </i>
          </div>
        );
      })}
    </div>
  );
}
export function EditList({
  items,
  selected,
  onChange,
}: {
  items: string[];
  selected: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <div className="group ref-edit-list">
      {items.map((item) => (
        <div className="ref-row" key={item}>
          <button
            className={
              "round-action " + (selected.includes(item) ? "remove" : "add")
            }
            aria-label={
              (selected.includes(item) ? "Quitar " : "Agregar ") + item
            }
            onClick={() =>
              onChange(
                selected.includes(item)
                  ? selected.filter((x) => x !== item)
                  : [...selected, item],
              )
            }
          >
            {selected.includes(item) ? <Minus size={12} /> : <Plus size={12} />}
          </button>
          <span>{item}</span>
          {selected.includes(item) && (
            <button
              className="icon-button"
              aria-label={"Mover " + item + " arriba"}
              onClick={() => {
                const pos = selected.indexOf(item);
                if (pos > 0) {
                  const next = [...selected];
                  [next[pos - 1], next[pos]] = [next[pos], next[pos - 1]];
                  onChange(next);
                }
              }}
            >
              <GripHorizontal size={15} />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
