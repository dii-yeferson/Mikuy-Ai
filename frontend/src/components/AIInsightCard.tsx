import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, body, soles } from "../api";
import { Button, ErrorBox, Sheet } from "./ui";
type Series = {
  label: string;
  unit: string;
  points: { date: string; value: number }[];
};
export type AIInsight = {
  id: string;
  kind: "progress" | "dining" | "goal";
  title: string;
  as_of: string;
  summary: string;
  series: Series[];
  facts: string[];
  recommendations: { text: string; reason: string }[];
  dishes: {
    name: string;
    supplied_text: string;
    price: number | null;
    budget_status: string;
    cautions: string[];
    suggestion: string;
    nutrition_note: string;
  }[];
  action: null | {
    old_value: number | null;
    new_value: number;
    status: "pending" | "confirmed" | "cancelled";
    explanation: string;
  };
};
function Trend({ series }: { series: Series }) {
  const values = series.points.map((p) => p.value),
    lo = Math.min(...values),
    hi = Math.max(...values),
    span = hi - lo || 1;
  const first = Date.parse(series.points[0].date),
    last = Date.parse(series.points.at(-1)!.date),
    days = last - first || 1;
  const coordinates = series.points
    .map(
      (p) =>
        `${12 + ((Date.parse(p.date) - first) / days) * 276},${105 - ((p.value - lo) / span) * 80}`,
    )
    .join(" ");
  return (
    <figure className="ai-trend">
      <figcaption>
        {series.label} · {series.unit}
      </figcaption>
      {series.points.length > 1 && (
        <svg
          viewBox="0 0 300 130"
          role="img"
          aria-label={
            series.label +
            ": registros por fecha; consulta los valores en la tabla"
          }
        >
          <polyline
            points={coordinates}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          />
          {series.points.map((p, i) => (
            <circle
              key={p.date}
              cx={Number(coordinates.split(" ")[i].split(",")[0])}
              cy={Number(coordinates.split(" ")[i].split(",")[1])}
              r="3"
              fill="currentColor"
            />
          ))}
        </svg>
      )}
      <details>
        <summary>Ver {series.points.length} registros</summary>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>{series.unit}</th>
            </tr>
          </thead>
          <tbody>
            {series.points.map((p) => (
              <tr key={p.date}>
                <td>{p.date}</td>
                <td>{p.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
      <small>
        Solo puntos registrados; los intervalos no representan mediciones
        adicionales.
      </small>
    </figure>
  );
}
export function AIInsightCard({ insight }: { insight: AIInsight }) {
  const [view, setView] = useState(insight),
    [confirm, setConfirm] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => setView(insight), [insight]);
  async function decide(decision: "confirm" | "cancel") {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<AIInsight>(
        "/coach-insights/" + view.id + "/decision",
        body("POST", { decision }),
      );
      setView(updated);
      setConfirm(false);
      if (decision === "confirm")
        window.dispatchEvent(new Event("profile-saved"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="ai-insight stack" aria-label={view.title}>
      <h2>{view.title}</h2>
      <small>Datos al {view.as_of}</small>
      <ul>
        {view.facts.map((f) => (
          <li key={f}>{f}</li>
        ))}
      </ul>
      {view.series.map((s) => (
        <Trend key={s.label} series={s} />
      ))}
      {view.recommendations.map((r) => (
        <div className="card" key={r.text}>
          <strong>{r.text}</strong>
          <p>{r.reason}</p>
        </div>
      ))}
      {view.dishes.map((d, i) => (
        <article className="card" key={i}>
          <h3>{d.name}</h3>
          <p>
            {d.price !== null
              ? soles(d.price) + " según tu carta"
              : "Precio no indicado"}{" "}
            ·{" "}
            {d.budget_status === "dentro"
              ? "Dentro del presupuesto indicado"
              : d.budget_status === "fuera"
                ? "Supera el presupuesto indicado"
                : "Presupuesto sin comparar"}
          </p>
          <details>
            <summary>Revisar plato</summary>
            <p>{d.supplied_text}</p>
            {d.cautions.map((c) => (
              <p key={c}>{c}</p>
            ))}
            <p>{d.suggestion}</p>
            <small>{d.nutrition_note}</small>
          </details>
          {d.cautions.length > 0 && (
            <small>Requiere confirmar ingredientes y restricciones.</small>
          )}
        </article>
      ))}
      {view.kind === "progress" && (
        <div className="proposal-links">
          <Link to="/diario">Abrir diario</Link>
          <Link to="/progreso">Ver progreso</Link>
          <Link to="/menu">Revisar menú</Link>
        </div>
      )}
      {view.action && (
        <div className="card">
          <p>
            Meta: {view.action.old_value ?? "sin configurar"} →{" "}
            {view.action.new_value} kcal
          </p>
          <small>{view.action.explanation}</small>
          {view.action.status === "pending" ? (
            <div className="proposal-actions">
              <Button onClick={() => setConfirm(true)} disabled={busy}>
                Revisar cambio
              </Button>
              <Button
                secondary
                onClick={() => void decide("cancel")}
                disabled={busy}
              >
                Cancelar cambio
              </Button>
            </div>
          ) : (
            <p role="status">
              {view.action.status === "confirmed"
                ? "Objetivo guardado"
                : "Cambio cancelado; no se modificó el objetivo"}
            </p>
          )}
        </div>
      )}
      <ErrorBox error={error} />
      {confirm && view.action && (
        <Sheet
          title="Confirmar objetivo"
          onClose={() => {
            if (!busy) setConfirm(false);
          }}
        >
          <p>
            Guardar {view.action.new_value} kcal como meta diaria solicitada.
            Esto no cambia automáticamente tu menú.
          </p>
          <ErrorBox error={error} />
          <Button busy={busy} onClick={() => void decide("confirm")}>
            Confirmar objetivo
          </Button>
          <Button
            secondary
            disabled={busy}
            onClick={() => void decide("cancel")}
          >
            Cancelar cambio
          </Button>
        </Sheet>
      )}
    </section>
  );
}
