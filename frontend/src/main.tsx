import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Dock, Spinner, Toasts } from "./components/Chrome";
import PremiumSheet from "./components/PremiumSheet";
import { RecipeProvider } from "./components/RecipeSheet";
import { StoreProvider, useStore } from "./lib/store";
import Assistant from "./pages/Assistant";
import Onboarding from "./pages/Onboarding";
import PlanPage from "./pages/PlanPage";
import Recipes from "./pages/Recipes";
import Settings from "./pages/Settings";
import Shopping from "./pages/Shopping";
import Today from "./pages/Today";
import Welcome from "./pages/Welcome";
import "./styles.css";

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);
  return null;
}

function App() {
  const { me, ready } = useStore();
  if (!ready) {
    return (
      <div className="hero" style={{ justifyContent: "center", alignItems: "center" }}>
        <img className="hero-logo" src="/icons/logo-mark.webp" alt="Mikuy" style={{ width: 110, margin: 0 }} />
        <span className="gold"><Spinner /></span>
      </div>
    );
  }
  if (!me) return <Welcome />;
  if (!me.profile.onboarded) return <Onboarding />;
  return (
    <RecipeProvider>
      <ScrollTop />
      <Routes>
        <Route path="/" element={<Today />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/ia" element={<Assistant />} />
        <Route path="/compras" element={<Shopping />} />
        <Route path="/recetas" element={<Recipes />} />
        <Route path="/ajustes" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Dock />
      <PremiumSheet />
    </RecipeProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <StoreProvider>
        <div className="aura" aria-hidden="true" />
        <div className="shell">
          <App />
        </div>
        <Toasts />
      </StoreProvider>
    </BrowserRouter>
  </StrictMode>
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
