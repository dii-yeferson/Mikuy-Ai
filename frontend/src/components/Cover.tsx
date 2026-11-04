import type { CSSProperties } from "react";
import type { RecipeSummary } from "../lib/types";

/** Portada ilustrada y animada mientras no haya foto. Si la receta trae `image`, se muestra la foto. */
const RULES: [RegExp, string, string?][] = [
  [/cebiche|tiradito|leche de tigre/, "🐟", "🍋"],
  [/causa/, "🥔", "🥑"],
  [/chaufa|aeropuerto|arroz con|arroz a la|arroz verde|arroz con mariscos/, "🍚", "🥢"],
  [/tallar|fideo|lasa|pasta/, "🍝", "🧀"],
  [/sopa|caldo|chupe|aguadito|sancochado|menestr|chairo|chilcano|crema|parihuela|shambar|inchicapi|wantan/, "🍲", "🌿"],
  [/ensalada|solterito/, "🥗", "🍅"],
  [/pollo|gallina|aji de gallina|pavita/, "🍗", "🌶️"],
  [/lomo|\bres\b|bistec|anticucho|carne|\bseco\b|estofado|olluquito|tacu/, "🥩", "🍟"],
  [/cerdo|chancho|chicharr|adobo|costilla/, "🥓", "🍠"],
  [/pescado|trucha|bonito|jurel|caballa|merluza|tilapia|sudado|chorrillana|jalea|pota|choros|langostino/, "🐠", "🍋"],
  [/cuy|alpaca|cordero|pachamanca/, "🍖", "🌽"],
  [/huevo|tortilla|omelette|revuelto/, "🍳", "🍅"],
  [/avena|quinua|kiwicha|mazamorra|\bapi\b|cereal|bowl|pudín|chía/, "🥣", "🍎"],
  [/\bpan\b|sangu|sángu|butifarra|wrap|tostada/, "🥪", "🥑"],
  [/panqueque/, "🥞", "🍌"],
  [/batido|jugo|chicha|emoliente|limonada|refresco/, "🥤", "🍓"],
  [/postre|arroz con leche|helado|leche asada|mousse|picarones|bombon|barritas/, "🍮", "✨"],
  [/fruta|papaya|platano|plátano|manzana|mandarina|yogur/, "🍓", "🍌"],
  [/lenteja|frejol|pallar|garbanzo|arveja/, "🫘", "🍚"],
  [/tofu|champi/, "🍄", "🥦"],
  [/papa|camote|yuca|humita|tamal|choclo|mote|tacacho|juane/, "🌽", "🥔"],
  [/pizza/, "🍕", "🌿"],
  [/hamburgues/, "🍔", "🥬"],
];

const PALETTES: Record<string, [string, string]> = {
  desayuno: ["#ffd98a", "#f7a541"],
  almuerzo: ["#ffb36b", "#e3612f"],
  cena: ["#9fb4ff", "#5b5bd6"],
  snack: ["#ffb3c7", "#e66b9a"],
};

function hash(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

const SIDES: [RegExp, string][] = [
  [/fresa/, "🍓"], [/manzana/, "🍎"], [/pl[aá]tano/, "🍌"], [/mango/, "🥭"], [/piña/, "🍍"], [/papaya/, "🧡"],
  [/palta/, "🥑"], [/lim[oó]n/, "🍋"], [/huevo/, "🥚"], [/queso/, "🧀"], [/cacao|chocolate/, "🍫"], [/man[ií]\b|nuez|pecana/, "🥜"],
  [/tomate/, "🍅"], [/camote|papa/, "🥔"], [/choclo|maíz|maiz/, "🌽"], [/arroz/, "🍚"], [/aj[ií]|rocoto/, "🌶️"], [/uva/, "🍇"],
];

export function emojiFor(name: string): [string, string] {
  const n = name.toLowerCase();
  const side = SIDES.find(([re]) => re.test(n))?.[1];
  for (const [re, main, def] of RULES) if (re.test(n)) return [main, side && side !== main ? side : def ?? "✨"];
  return ["🍽️", side ?? "✨"];
}

export default function Cover({ recipe, size, className = "" }: { recipe: Pick<RecipeSummary, "id" | "name" | "meal" | "tags" | "image">; size?: number; className?: string }) {
  const h = hash(recipe.id);
  const [a, b] = PALETTES[recipe.meal] ?? PALETTES.almuerzo;
  const angle = 120 + (h % 90);
  const [main, side] = emojiFor(recipe.name);
  const hot = !recipe.tags.includes("sin-coccion") && !/ensalada|batido|jugo|helado|yogur|fruta|cebiche|tiradito|limonada/i.test(recipe.name);
  const style = {
    "--cover-bg": `linear-gradient(${angle}deg, ${a}, ${b})`,
    "--cx": `${20 + (h % 60)}%`,
    "--cy": `${15 + ((h >> 3) % 50)}%`,
    ...(size ? { "--size": `${size}px` } : {}),
  } as CSSProperties;
  return (
    <div className={`cover ${className}`} style={style} aria-hidden="true">
      {recipe.image ? (
        <img className="photo" src={recipe.image} alt="" loading="lazy" />
      ) : (
        <>
          {hot && (
            <>
              <i className="steam" />
              <i className="steam" />
              <i className="steam" />
            </>
          )}
          <span className="emoji" style={{ animationDelay: `-${h % 4}s` }}>{main}</span>
          <span className="emoji side" style={{ right: "12%", bottom: "12%", animationDelay: `-${h % 3}s` }}>{side}</span>
          <i className="spark" style={{ left: `${15 + (h % 30)}%`, top: "22%", animationDelay: `-${h % 3}s` }} />
          <i className="spark" style={{ left: "72%", top: `${18 + (h % 20)}%`, animationDelay: `-${(h >> 2) % 4}s` }} />
        </>
      )}
    </div>
  );
}
