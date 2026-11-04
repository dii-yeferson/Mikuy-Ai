export type Meal = "desayuno" | "almuerzo" | "cena" | "snack";

export interface Profile {
  onboarded: boolean;
  goal: "bajar" | "mantener" | "subir" | "comer-mejor" | "ahorrar";
  sex: "mujer" | "hombre";
  age: number;
  weight_kg: number;
  height_cm: number;
  activity: "sedentaria" | "ligera" | "moderada" | "intensa";
  diet: "omnivoro" | "vegetariano" | "vegano" | "pescetariano" | "sin-gluten";
  allergies: string[];
  excluded: string[];
  conditions: string[];
  city: string;
  people: number;
  weekly_budget: number;
  max_minutes: number;
  snacks: boolean;
  sounds: boolean;
  haptics: boolean;
  voice_reply: boolean;
  theme: "auto" | "claro" | "oscuro";
  favorites: string[];
}

export interface Subscription {
  plan: "gratis" | "premium" | "familia";
  plan_name: string;
  period: string | null;
  expires_at: string | null;
  premium: boolean;
  simulated: boolean;
  people_limit: number;
  limits: null | { ai_per_day: number; ai_used_today: number; plans_per_week: number; plans_used_week: number };
}

export interface Me {
  id: string;
  name: string;
  email: string;
  profile: Profile;
  subscription: Subscription;
}

export interface RecipeSummary {
  id: string;
  name: string;
  meal: Meal;
  minutes: number;
  tags: string[];
  region: string;
  kcal: number;
  protein: number;
  cost: number;
  diet: string[];
  image: string | null;
  favorite?: boolean;
  allowed?: boolean;
}

export interface Nutrition {
  kcal: number;
  protein: number;
  fat: number;
  carbs: number;
  fiber: number;
  sodium: number;
  free_sugar: number;
}

export interface RecipeDetail extends Omit<RecipeSummary, "kcal" | "protein"> {
  portion: number;
  ingredients: { id: string; name: string; qty: number; unit: string; cost: number; unit_price: number; price_unit: string }[];
  steps: string[];
  nutrition: Nutrition;
  allergens: string[];
  warnings: string[];
}

export interface PlanMeal {
  meal: Meal;
  label: string;
  portion: number;
  recipe: RecipeSummary;
  kcal: number;
  protein: number;
  cost: number;
}

export interface Targets {
  kcal: number;
  protein: number;
  fat: number;
  carbs: number;
  fiber: number;
  sodium: number;
  bmr: number;
  tdee: number;
  bmi: number;
  method: string;
}

export interface Plan {
  id: string;
  week_start: string;
  version: number;
  days: { day: string; date: string; meals: PlanMeal[] }[];
  summary: {
    week_cost: number;
    budget: number;
    within_budget: boolean | null;
    per_person_day: number;
    avg: Record<string, number>;
    days: { date: string; kcal: number; protein: number; cost: number }[];
    targets: Targets;
  };
}

export interface ShopItem {
  id: string;
  name: string;
  need: string;
  buy: string;
  buy_cost: number;
  used_cost: number;
  unit_price: number;
  price_unit: string;
  pantry: boolean;
  checked: boolean;
  hidden?: boolean;
  recipes: string[];
}

export interface Shopping {
  city: string;
  people: number;
  sections: { id: string; name: string; items: ShopItem[] }[];
  total_buy: number;
  total_used: number;
  pending: number;
  include_pantry: boolean;
  count: number;
  text: string;
}

export interface Card {
  type: "swap" | "plan" | "savings" | "profile" | "recipe" | "shopping";
  [k: string]: any;
}

export interface ChatMessage {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  cards: Card[];
  created_at?: string;
  pending?: boolean;
}

export interface Source {
  id: string;
  topic: string;
  title: string;
  publisher: string;
  url: string;
  use: string;
}

export interface CatalogMeta {
  cities: { id: string; name: string; region: string }[];
  price_date: string;
  price_note: string;
  nutrition_note: string;
  sources: Source[];
  recipes: number;
  ingredients: { id: string; name: string }[];
}
