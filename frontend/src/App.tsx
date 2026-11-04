import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
  useLocation,
} from "react-router-dom";
import { AppProvider, useApp } from "./context";
import { BottomNav, ErrorBox, Loading } from "./components/ui";
import { Welcome, Auth } from "./pages/Auth";
import {
  ReconstructedOnboarding,
  JoinPage,
} from "./pages/ReconstructionOnboarding";
import { PlanPage, HistoryPage } from "./pages/Plan";
import { ShoppingPage, LatestShoppingPage } from "./pages/Shopping";
import { TodayPage } from "./pages/Today";
import { RecipesPage } from "./pages/Recipes";
import { ReportPage } from "./pages/Report";
import { CoachPage } from "./pages/Coach";
import { ReferencePlan, FavoritesPage } from "./pages/ReferencePlan";
import { ReferenceSettings } from "./pages/ReferenceSettings";
import {
  ReferenceProgress,
  PhotosPage,
  NotesPage,
  StreakPage,
  ActivityPage,
  RecordMetricPage,
} from "./pages/ReferenceProgress";
import {
  ReferenceSocial,
  ReferenceProfile,
  CapturePage,
  FastingPage,
} from "./pages/ReferenceCommunity";
import { ExperienceRuntime } from "./components/ExperienceRuntime";
import { ReferenceSubscription } from "./pages/ReferenceSubscription";
import { ProfilePage, ExplanationPage, PrivacyPage } from "./pages/Settings";

function Private() {
  const { user, loading, error } = useApp();
  if (loading) return <Loading />;
  if (error && !user)
    return (
      <div className="page">
        <ErrorBox error={error} retry={() => window.location.reload()} />
      </div>
    );
  return user ? <Outlet /> : <Navigate to="/ingresar" replace />;
}
function Layout() {
  const { pathname } = useLocation();
  const navigation = [
    "/hoy",
    "/diario",
    "/menu",
    "/compras",
    "/coach",
    "/social",
    "/progreso",
    "/recetas",
  ].includes(pathname);
  return (
    <div className={"route-panel " + (navigation ? "with-nav" : "")}>
      <Outlet />
      {navigation && <BottomNav />}
    </div>
  );
}
function ScrollReset() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}
function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const lost = () => setOffline(true),
      restored = () => setOffline(false);
    window.addEventListener("online", restored);
    window.addEventListener("offline", lost);
    window.addEventListener("connection-lost", lost);
    window.addEventListener("connection-restored", restored);
    return () => {
      window.removeEventListener("online", restored);
      window.removeEventListener("offline", lost);
      window.removeEventListener("connection-lost", lost);
      window.removeEventListener("connection-restored", restored);
    };
  }, []);
  return offline ? (
    <div className="offline" role="status">
      Sin conexión con Mikuy. Tus datos necesitan internet; los formularios
      abiertos se conservan en esta ventana.
    </div>
  ) : null;
}
export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <ScrollReset />
        <ExperienceRuntime />
        <div className="app-shell">
          <OfflineBanner />
          <Routes>
            <Route path="/" element={<Welcome />} />
            <Route path="/registro" element={<Auth register />} />
            <Route path="/ingresar" element={<Auth />} />
            <Route path="/privacidad" element={<PrivacyPage />} />
            <Route path="/onboarding" element={<ReconstructedOnboarding />} />
            <Route path="/unirse" element={<JoinPage />} />
            <Route element={<Private />}>
              <Route element={<Layout />}>
                <Route path="/hoy" element={<TodayPage />} />
                <Route path="/menu" element={<PlanPage />} />
                <Route path="/compras" element={<LatestShoppingPage />} />
                <Route path="/recetas" element={<RecipesPage />} />
                <Route path="/reporte" element={<ReportPage />} />
                <Route path="/diario" element={<ReferencePlan />} />
                <Route path="/plan" element={<Navigate to="/hoy" replace />} />
                <Route
                  path="/planes/semanal"
                  element={<Navigate to="/menu" replace />}
                />
                <Route path="/compras/:id" element={<ShoppingPage />} />
                <Route path="/historial" element={<HistoryPage />} />
                <Route path="/coach" element={<CoachPage />} />
                <Route path="/progreso" element={<ReferenceProgress />} />
                <Route path="/progreso/fotos" element={<PhotosPage />} />
                <Route
                  path="/progreso/:metric"
                  element={<ReferenceProgress />}
                />
                <Route path="/social" element={<ReferenceSocial />} />
                <Route path="/ajustes" element={<ReferenceSettings />} />
                <Route
                  path="/ajustes/:section"
                  element={<ReferenceSettings />}
                />
                <Route path="/perfil" element={<ReferenceProfile />} />
                <Route path="/cuenta/datos" element={<ProfilePage />} />
                <Route path="/notas" element={<NotesPage />} />
                <Route path="/rachas" element={<StreakPage />} />
                <Route path="/actividad" element={<ActivityPage />} />
                <Route path="/registro/:kind" element={<RecordMetricPage />} />
                <Route path="/favoritos" element={<FavoritesPage />} />
                <Route path="/captura" element={<CapturePage />} />
                <Route path="/ayuno" element={<FastingPage />} />
                <Route
                  path="/suscripcion"
                  element={<ReferenceSubscription />}
                />
                <Route
                  path="/suscripcion/:view"
                  element={<ReferenceSubscription />}
                />
              </Route>
            </Route>
            <Route path="*" element={<ExplanationPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AppProvider>
  );
}
