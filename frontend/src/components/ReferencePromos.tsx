import { useState } from "react";
import { Camera, Image } from "lucide-react";
import { Card } from "./ui";
import type { OnboardingAnswers } from "../experience";

export function ReferencePromo({
  kind,
  answers,
}: {
  kind: string;
  answers: OnboardingAnswers;
}) {
  const [slide, setSlide] = useState(0);
  if (kind === "comparacion")
    return (
      <div className="reference-comparison">
        <div className="comparison-bars">
          <div>
            <strong>—</strong>
            <span>Sin Mikuy</span>
          </div>
          <div>
            <strong>—</strong>
            <span>Con Mikuy</span>
          </div>
        </div>
        <p>No hay datos propios de Mikuy para comparar resultados.</p>
      </div>
    );
  if (kind === "evolucion")
    return (
      <div className="reference-evolution">
        <span className="badge">Registro de tu progreso</span>
        <small>Tu peso</small>
        <svg
          viewBox="0 0 330 210"
          role="img"
          aria-label="Peso inicial declarado, sin predicción"
        >
          <defs>
            <linearGradient id="evolution">
              <stop stopColor="#176447" stopOpacity=".5" />
              <stop offset="1" stopColor="#176447" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[70, 115, 160, 205].map((v) => (
            <path
              key={v}
              d={"M10 " + v + "H320"}
              stroke="#333"
              strokeDasharray="4 4"
            />
          ))}
          <circle cx="20" cy="70" r="8" fill="var(--leaf)" />
          <text x="35" y="65" fill="white" fontSize="15">
            {answers.weight ?? "—"} kg
          </text>
          <text x="95" y="130" fill="#999" fontSize="14">
            Aún no hay más registros
          </text>
        </svg>
        <p>
          La evolución aparecerá con tus registros reales. No se garantiza un
          resultado ni una fecha.
        </p>
      </div>
    );
  if (kind === "testimonios")
    return (
      <div className="reference-testimonials">
        <div className="testimonial-pair">
          {["Antes", "Después"].map((v) => (
            <div key={v}>
              <Image size={36} />
              <span>{v}</span>
              <strong>— kg</strong>
            </div>
          ))}
        </div>
        <p>Aún sin testimonios propios de Mikuy</p>
        <div className="ref-page-dots">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <button
              key={i}
              aria-label={"Testimonio " + (i + 1)}
              className={slide === i ? "active" : ""}
              onClick={() => setSlide(i)}
            />
          ))}
        </div>
        <Card>
          <span>❧</span>
          <div>
            <strong>— / 5.0</strong>
            <p>Sin calificación publicada</p>
          </div>
          <span>❧</span>
        </Card>
      </div>
    );
  if (kind === "presentacion-scan")
    return (
      <div className="reference-scan-preview">
        <img
          src="/reference-art/food.webp"
          alt="Plato de pollo, arroz y brócoli de referencia"
        />
        <div>
          <span className="scan-label">
            <Camera size={17} /> Registro de comidas
          </span>
          <div className="welcome-macro-boxes">
            {["kcal", "proteínas", "carbs", "grasas"].map((v) => (
              <div key={v}>
                <strong>—</strong>
                <span>{v}</span>
              </div>
            ))}
          </div>
          <h3>Ingredientes</h3>
          <p>Pollo · arroz · brócoli</p>
          <small>
            Imagen de referencia. El reconocimiento con IA requiere un modelo
            visual configurado; el registro manual está disponible.
          </small>
        </div>
      </div>
    );
  return (
    <div className="reference-plan-preview">
      <header>
        Desayuno <small>Selecciona tus recetas</small>
      </header>
      <div>
        {[
          "Arroz con pollo y huevo",
          "Guiso de pollo y papas",
          "Quinua con verduras",
        ].map((name, i) => (
          <article key={name}>
            <img src={"/reference-art/recipe-" + (i + 1) + ".webp"} alt="" />
            <strong>{name}</strong>
          </article>
        ))}
      </div>
      <header>
        Almuerzo <small>Plan semanal</small>
      </header>
      <div>
        {[
          "Guiso de pollo y papas",
          "Quinua con verduras",
          "Arroz con pollo y huevo",
        ].map((name, i) => (
          <article key={name}>
            <img
              src={"/reference-art/recipe-" + (((i + 1) % 3) + 1) + ".webp"}
              alt=""
            />
            <strong>{name}</strong>
          </article>
        ))}
      </div>
      <header>Cena</header>
      <p>
        Las recetas del plan se filtran según las restricciones declaradas.
        Catálogo inicial estimativo.
      </p>
    </div>
  );
}
