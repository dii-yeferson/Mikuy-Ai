import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, body, soles } from "../api";
import { Button, ErrorBox, Field, Sheet } from "./ui";
export type CoachRecipe = {
  recipe_id: string;
  name: string;
  kind: string;
  servings: number;
  minutes: number;
  cost: number;
  cost_per_serving: number;
  ingredients: {
    ingredient_id: string;
    name: string;
    quantity: number;
    unit: string;
  }[];
  steps: string[];
  nutrition_per_serving: Record<string, number>;
  nutrition_total: Record<string, number>;
};
export type CoachProposal = {
  id: string;
  version: number;
  budget: number;
  servings: number;
  total: number;
  remaining: number;
  recipes: CoachRecipe[];
  price_note: string;
  nutrition_note: string;
  budget_note: string;
  source: string;
};
export function CoachPlanCards({ proposal }: { proposal: CoachProposal }) {
  const [p, setP] = useState(proposal),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [servings, setServings] = useState(String(proposal.servings)),
    [selection, setSelection] = useState<CoachRecipe[] | null>(null),
    [planId, setPlanId] = useState("");
  useEffect(() => {
    setP(proposal);
    setServings(String(proposal.servings));
  }, [proposal]);
  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function edit(change: object) {
    void run(async () => {
      const next = await api<CoachProposal>(
        "/coach-plans/" + p.id,
        body("PATCH", { expected_version: p.version, ...change }),
      );
      setP(next);
      setServings(String(next.servings));
      setNotice("Propuesta actualizada");
    });
  }
  async function apply(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await run(async () => {
      const result = await api<{ plan_id: string }>(
        "/coach-plans/" + p.id + "/apply",
        body("POST", {
          expected_version: p.version,
          placements: selection!.map((r) => ({
            recipe_id: r.recipe_id,
            date: f.get("date"),
            meal: String(f.get("meal-" + r.recipe_id)),
          })),
        }),
      );
      setPlanId(result.plan_id);
      setSelection(null);
      setNotice("Menú guardado y compras consolidadas");
    });
  }
  return (
    <section className="coach-plan-cards" aria-label="Propuesta de comidas">
      <header>
        <h2>Tu propuesta</h2>
        <p>{p.servings} persona(s) · Ingredientes estimados</p>
        <div className="proposal-budget">
          <span>
            Total <strong>{soles(p.total)}</strong>
          </span>
          <span>
            Presupuesto <strong>{soles(p.budget)}</strong>
          </span>
          <span>
            Margen <strong>{soles(p.remaining)}</strong>
          </span>
        </div>
      </header>
      <form
        className="proposal-portions"
        onSubmit={(e) => {
          e.preventDefault();
          edit({ servings: Number(servings) });
        }}
      >
        <Field label="Personas / porciones">
          <input
            type="number"
            min="1"
            max="6"
            required
            value={servings}
            onChange={(e) => setServings(e.target.value)}
            disabled={busy}
          />
        </Field>
        <Button secondary disabled={busy || Number(servings) === p.servings}>
          Recalcular
        </Button>
      </form>
      {p.recipes.map((r) => (
        <article className="card proposal-recipe" key={r.kind}>
          <small className="section-title">{r.kind}</small>
          <h3>{r.name}</h3>
          <p>
            {r.servings} porción(es) · {r.minutes} min ·{" "}
            {soles(r.cost_per_serving)} por porción aprox.
          </p>
          <details>
            <summary>Ingredientes y preparación</summary>
            <h4>Para {r.servings} porción(es)</h4>
            <ul>
              {r.ingredients.map((i) => (
                <li key={i.ingredient_id}>
                  {i.quantity} {i.unit} · {i.name}
                </li>
              ))}
            </ul>
            <h4>Preparación</h4>
            <ol>
              {r.steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
            <p>
              Nutrición estimada por porción: {r.nutrition_per_serving.kcal}{" "}
              kcal · proteína {r.nutrition_per_serving.protein} g ·
              carbohidratos {r.nutrition_per_serving.carbs} g · grasa{" "}
              {r.nutrition_per_serving.fat} g.
            </p>
            <p>
              Total de {r.servings} porción(es): {r.nutrition_total.kcal} kcal.
            </p>
            <small>{p.nutrition_note}</small>
          </details>
          <div className="proposal-actions">
            <Button
              secondary
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api(
                    "/coach-plans/" + p.id + "/save",
                    body("POST", {
                      recipe_id: r.recipe_id,
                      expected_version: p.version,
                    }),
                  );
                  setNotice("Guardada en Mis recetas");
                })
              }
            >
              Guardar receta
            </Button>
            <Button secondary disabled={busy} onClick={() => setSelection([r])}>
              Añadir al menú
            </Button>
            <Button
              secondary
              disabled={busy}
              onClick={() => edit({ replace_kind: r.kind })}
            >
              Sustituir {r.kind.toLowerCase()}
            </Button>
          </div>
        </article>
      ))}
      <small>
        {p.price_note} {p.budget_note}
      </small>
      {p.source === "catalogo_respaldo" && (
        <small>
          El proveedor de IA no estuvo disponible; se usó una selección calculada del
          catálogo.
        </small>
      )}
      <ErrorBox error={error} />
      <p role="status">{busy ? "Procesando…" : notice}</p>
      <Button disabled={busy} onClick={() => setSelection(p.recipes)}>
        Añadir todo y generar compras
      </Button>
      <div className="proposal-links">
        <Link to="/recetas?guardadas=1">Mis recetas</Link>
        {planId && (
          <>
            <Link to={"/menu?id=" + planId}>Ver menú</Link>
            <Link to={"/compras/" + planId}>Ver compras</Link>
          </>
        )}
      </div>
      {selection && (
        <Sheet
          title="Confirmar comidas"
          onClose={() => {
            if (!busy) setSelection(null);
          }}
        >
          <form className="stack" onSubmit={apply}>
            <Field label="Fecha de las comidas">
              <input name="date" type="date" required disabled={busy} />
            </Field>
            <p>
              Confirma la fecha y la comida de cada receta. Las comidas
              existentes no se sobrescriben.
            </p>
            {selection.map((r) => (
              <Field key={r.recipe_id} label={"Comida para " + r.name}>
                <select
                  name={"meal-" + r.recipe_id}
                  defaultValue={r.kind}
                  disabled={busy}
                >
                  {["Desayuno", "Almuerzo", "Cena"].map((kind) => (
                    <option key={kind}>{kind}</option>
                  ))}
                </select>
              </Field>
            ))}
            <ErrorBox error={error} />
            <Button busy={busy}>Confirmar y guardar</Button>
          </form>
        </Sheet>
      )}
    </section>
  );
}
