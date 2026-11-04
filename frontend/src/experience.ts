import { useEffect, useRef, useState } from "react";
import { api, body } from "./api";
import { useApp } from "./context";
import { defaultProfile, type Profile } from "./types";

export type MealName = "Desayuno" | "Almuerzo" | "Cena" | "Snack 1" | "Snack 2";
export const mealNames: MealName[] = [
  "Desayuno",
  "Almuerzo",
  "Cena",
  "Snack 1",
  "Snack 2",
];
export type Reminder = {
  enabled: boolean;
  time: string;
  days: number[];
  interval_hours: number;
};
export type ExperienceSettings = {
  appearance: "Tema del dispositivo" | "Claro" | "Oscuro";
  vibration: boolean;
  food_weight: "g" | "oz";
  liquid_volume: "ml" | "fl oz";
  body_weight: "kg" | "lb";
  height_unit: "cm" | "ft/in";
  energy_unit: "kcal" | "kJ";
  calorie_target: number | null;
  protein_percent: number;
  carbs_percent: number;
  fat_percent: number;
  meal_distribution: Partial<Record<MealName, number>>;
  visible_cards: string[];
  nutrients: string[];
  charts: string[];
  reminders: Record<string, Reminder>;
  coach_alerts: boolean;
  coach_consent: boolean;
  coach_intro_seen: boolean;
  coach_memories: string[];
  copy_yesterday: boolean;
  portion_adjustment: boolean;
  plateau_detection: boolean;
  auto_calories: boolean;
  calories_by_day: boolean;
  public_profile: boolean;
  description: string;
  dismissed_banners: string[];
};
export type OnboardingAnswers = {
  step: string;
  method: string;
  obstacles: string[];
  previous: string[];
  tedious: string;
  knowledge: string;
  sex: "" | "Hombre" | "Mujer" | "Prefiero no decir";
  age: number | null;
  height: number | null;
  weight: number | null;
  target_weight: number | null;
  strength: boolean | null;
  lifestyle: string;
  diet_style: string;
  speed: string;
  extra_goals: string[];
  rating: number | null;
  acquisition: string;
};
export const defaultSettings: ExperienceSettings = {
  appearance: "Oscuro",
  vibration: true,
  food_weight: "g",
  liquid_volume: "ml",
  body_weight: "kg",
  height_unit: "cm",
  energy_unit: "kcal",
  calorie_target: null,
  protein_percent: 23,
  carbs_percent: 47,
  fat_percent: 30,
  meal_distribution: { Desayuno: 31.3, Almuerzo: 40.6, Cena: 28.1 },
  visible_cards: [
    "Desayuno",
    "Almuerzo",
    "Cena",
    "Meds y Suplementos",
    "Actividad",
    "Agua",
    "Pasos",
    "Notas",
  ],
  nutrients: ["Azúcares", "Fibra", "Sodio", "Grasas Saturadas"],
  charts: ["Calorías", "Peso Balanza", "% Grasa", "Fotos"],
  reminders: {},
  coach_alerts: true,
  coach_consent: false,
  coach_intro_seen: false,
  coach_memories: [],
  copy_yesterday: true,
  portion_adjustment: true,
  plateau_detection: false,
  auto_calories: false,
  calories_by_day: false,
  public_profile: false,
  description: "",
  dismissed_banners: [],
};
export const defaultAnswers: OnboardingAnswers = {
  step: "objetivo",
  method: "",
  obstacles: [],
  previous: [],
  tedious: "",
  knowledge: "",
  sex: "",
  age: null,
  height: null,
  weight: null,
  target_weight: null,
  strength: null,
  lifestyle: "",
  diet_style: "Recomendada",
  speed: "Recomendado",
  extra_goals: [],
  rating: null,
  acquisition: "",
};
export function completeProfile(
  p: Profile,
): Profile & { settings: ExperienceSettings; onboarding: OnboardingAnswers } {
  return {
    ...p,
    settings: { ...defaultSettings, ...p.settings },
    onboarding: { ...defaultAnswers, ...p.onboarding },
  };
}
export function useProfileEditor() {
  const { user, notify } = useApp();
  const [profile, setProfile] = useState(completeProfile(defaultProfile)),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const current = useRef(profile);
  const confirmed = useRef(profile);
  const queue = useRef(Promise.resolve());
  const pending = useRef(0);
  const path = user ? "/profile" : "/onboarding/draft";
  useEffect(() => {
    const controller = new AbortController();
    api<Profile>(path, { signal: controller.signal })
      .then((p) => {
        current.current = completeProfile(p);
        confirmed.current = current.current;
        setProfile(current.current);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path]);
  const save = (patch: Partial<Profile>, message?: string): Promise<void> => {
    const next = completeProfile({ ...current.current, ...patch });
    current.current = next;
    setProfile(next);
    setBusy(true);
    setError("");
    pending.current++;
    const job = queue.current
      .catch(() => {})
      .then(async () => {
        try {
          const persisted = completeProfile(
            await api<Profile>(path, body("PUT", next)),
          );
          confirmed.current = persisted;
          if (current.current === next) {
            current.current = persisted;
            setProfile(persisted);
          }
          window.dispatchEvent(
            new CustomEvent("profile-saved", { detail: persisted }),
          );
          if (message) notify(message);
        } catch (e) {
          if (current.current === next) {
            current.current = confirmed.current;
            setProfile(confirmed.current);
          }
          setError((e as Error).message);
          throw e;
        } finally {
          pending.current--;
          setBusy(pending.current > 0);
        }
      });
    queue.current = job;
    return job;
  };
  const setting = <K extends keyof ExperienceSettings>(
    key: K,
    value: ExperienceSettings[K],
  ) => save({ settings: { ...current.current.settings, [key]: value } });
  return { profile, save, setting, loading, busy, error };
}
export type Food = {
  id: string;
  date: string;
  meal: MealName;
  name: string;
  quantity: number;
  unit: string;
  kcal: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  sugar: number;
  sodium: number;
  saturated: number;
  nutrition_declared: boolean;
};
export type Diary = {
  date: string;
  foods: Food[];
  totals: Record<
    | "kcal"
    | "protein"
    | "carbs"
    | "fat"
    | "fiber"
    | "sugar"
    | "sodium"
    | "saturated",
    number
  >;
  finished: boolean;
  nutrition_source: string;
};

export const normalizeText = (s: string) =>
  s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
