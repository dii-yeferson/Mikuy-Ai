import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Camera, Mic, Square } from "lucide-react";
import { api, body, today } from "../api";
import { useApp } from "../context";
import { useDictation } from "../useDictation";
import { Button, ErrorBox, Field, Sheet } from "./ui";

export function QuickRegister({
  onClose,
  initialMeal = "Desayuno",
}: {
  onClose: () => void;
  initialMeal?: string;
}) {
  const [tab, setTab] = useState("Registrar"),
    [name, setName] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [voiceConsent, setVoiceConsent] = useState(false);
  const voice = useDictation(name, setName);
  const { notify } = useApp();
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      const saved = await api<{ id: string }>(
        "/diary",
        body("POST", {
          date: today(),
          meal: String(form.get("meal")),
          name: name.trim(),
          kcal: Number(form.get("kcal")),
          nutrition_declared: true,
        }),
      );
      window.dispatchEvent(new Event("diary-updated"));
      notify("Comida registrada", async () => {
        await api("/diary/food/" + saved.id, body("DELETE"));
        window.dispatchEvent(new Event("diary-updated"));
      });
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Sheet
      title={"Registrar · " + initialMeal}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <div className="segments">
        {["Registrar", "Explorar"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={tab === t ? "active" : ""}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Registrar" ? (
        <form className="stack quick-register" onSubmit={save}>
          <Field label="Comida">
            <select name="meal" defaultValue={initialMeal}>
              {["Desayuno", "Almuerzo", "Cena", "Snack 1", "Snack 2"].map(
                (m) => (
                  <option key={m}>{m}</option>
                ),
              )}
            </select>
          </Field>
          <Field label="¿Qué comiste?">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={120}
              placeholder="Ej. yogur con fruta"
            />
          </Field>
          <div className="quick-register-tools">
            <button
              type="button"
              className="text-button"
              onClick={() => {
                if (voice.listening) voice.stop();
                else if (voiceConsent) voice.start();
                else setVoiceConsent(true);
              }}
            >
              {voice.listening ? <Square size={17} /> : <Mic size={17} />}{" "}
              {voice.listening ? "Detener dictado" : "Dictar nombre"}
            </button>
            <Link to="/captura" onClick={onClose}>
              <Camera size={17} /> Foto
            </Link>
          </div>
          {voiceConsent && !voice.listening && (
            <small>
              El navegador puede procesar tu voz con su proveedor. Pulsa “Dictar
              nombre” para comenzar y revisa el texto.
            </small>
          )}
          <Field label="Calorías (kcal)">
            <input
              name="kcal"
              type="number"
              min="0"
              max="10000"
              step="0.1"
              required
              placeholder="Según etiqueta o porción"
            />
          </Field>
          <small>
            Registra las calorías de la porción que consumiste. Los nutrientes
            no declarados no se estiman automáticamente.
          </small>
          <ErrorBox error={error || voice.error} />
          <Button busy={busy} disabled={!name.trim() || voice.listening}>
            Guardar comida
          </Button>
        </form>
      ) : (
        <div className="group explore-links">
          {[
            ["/menu", "🍽️", "Menú semanal"],
            ["/compras", "🛒", "Compras"],
            ["/social", "👥", "Comunidad"],
            ["/diario", "📖", "Diario"],
            ["/progreso", "📊", "Progreso"],
            ["/recetas", "🥣", "Recetas"],
            ["/ajustes", "⚙️", "Ajustes"],
          ].map(([to, emoji, label]) => (
            <Link className="row" key={to} to={to} onClick={onClose}>
              <span>
                <span className="category-emoji">{emoji}</span>
                {label}
              </span>
              <span aria-hidden="true">›</span>
            </Link>
          ))}
        </div>
      )}
    </Sheet>
  );
}
