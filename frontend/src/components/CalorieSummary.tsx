import { useEffect, useState } from "react";
import { QuickRegister } from "./QuickRegister";
import { today } from "../api";
import { useResource } from "../hooks";
import type { Diary, ExperienceSettings, MealName } from "../experience";
import { ErrorBox } from "./ui";

export function CalorieSummary({
  settings,
}: {
  settings?: ExperienceSettings;
}) {
  const [selectedMeal, setSelectedMeal] = useState<string | null>(null);
  const diary = useResource<Diary>("/diary/" + today());
  useEffect(() => {
    window.addEventListener("diary-updated", diary.reload);
    return () => window.removeEventListener("diary-updated", diary.reload);
  }, [diary.reload]);
  return (
    <section className="calorie-summary" aria-label="Calorías registradas hoy">
      <p className="section-title">Registradas hoy</p>
      <div className="calorie-number">
        {diary.data
          ? Math.round(diary.data.totals.kcal).toLocaleString("es-PE")
          : "—"}
        <span>kcal</span>
      </div>
      <p className="muted">
        {settings?.calorie_target
          ? `Meta diaria: ${settings.calorie_target} kcal`
          : "Sin meta de calorías configurada"}
      </p>
      <ErrorBox error={diary.error} retry={diary.reload} />
      <div className="meal-progress-grid">
        {["Desayuno", "Almuerzo", "Cena", "Snacks"].map((meal, index) => {
          const amount =
            diary.data?.foods
              .filter((f) =>
                meal === "Snacks"
                  ? f.meal.startsWith("Snack")
                  : f.meal === meal,
              )
              .reduce((sum, f) => sum + f.kcal, 0) || 0;
          const d = settings?.meal_distribution;
          const percent =
            meal === "Snacks"
              ? (d?.["Snack 1"] || 0) + (d?.["Snack 2"] || 0)
              : d?.[meal as MealName] || 0;
          const goal = ((settings?.calorie_target || 0) * percent) / 100;
          return (
            <button
              type="button"
              className="meal-progress"
              onClick={() =>
                setSelectedMeal(meal === "Snacks" ? "Snack 1" : meal)
              }
              key={meal}
              aria-label={"Registrar " + meal}
            >
              <div className="meal-progress-track">
                <div
                  style={{
                    height: goal
                      ? `${Math.min(100, (amount / goal) * 100)}%`
                      : "0%",
                  }}
                />
                <span className="category-emoji">
                  {["🍳", "🍲", "🥣", "🍎"][index]}
                </span>
              </div>
              <strong>{diary.data ? Math.round(amount) : "—"}</strong>
              <span>{meal}</span>
              <small>{goal ? `de ${Math.round(goal)} kcal` : "Sin meta"}</small>
            </button>
          );
        })}
      </div>
      {selectedMeal && (
        <QuickRegister
          initialMeal={selectedMeal}
          onClose={() => setSelectedMeal(null)}
        />
      )}
    </section>
  );
}
