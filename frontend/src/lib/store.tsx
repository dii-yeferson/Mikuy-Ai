import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "./api";
import { feel, setFeelPrefs } from "./feel";
import type { CatalogMeta, Me, Plan, Profile } from "./types";

interface Toast {
  id: number;
  text: string;
  tone: "ok" | "error" | "info";
  action?: { label: string; run: () => void };
}

interface Store {
  me: Me | null;
  ready: boolean;
  plan: Plan | null;
  meta: CatalogMeta | null;
  setMe: (m: Me | null) => void;
  refreshMe: () => Promise<void>;
  setPlan: (p: Plan | null) => void;
  loadPlan: () => Promise<void>;
  saveProfile: (changes: Partial<Profile>) => Promise<void>;
  toast: (text: string, tone?: Toast["tone"], action?: Toast["action"]) => void;
  toasts: Toast[];
  premiumOpen: boolean;
  openPremium: (open?: boolean) => void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [me, setMeState] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [meta, setMeta] = useState<CatalogMeta | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [premiumOpen, setPremiumOpen] = useState(false);
  const seq = useRef(0);

  const toast = useCallback((text: string, tone: Toast["tone"] = "ok", action?: Toast["action"]) => {
    const id = ++seq.current;
    setToasts((t) => [...t.slice(-2), { id, text, tone, action }]);
    if (tone === "error") feel("error");
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), action ? 6000 : 3200);
  }, []);

  const setMe = useCallback((m: Me | null) => {
    setMeState(m);
    if (m) setFeelPrefs({ sounds: m.profile.sounds, haptics: m.profile.haptics });
  }, []);

  const refreshMe = useCallback(async () => {
    try {
      setMe(await api.get<Me>("/api/auth/me"));
    } catch {
      setMe(null);
    }
  }, [setMe]);

  const loadPlan = useCallback(async () => {
    try {
      const r = await api.get<{ plan: Plan | null }>("/api/plan");
      setPlan(r.plan);
    } catch {
      setPlan(null);
    }
  }, []);

  const saveProfile = useCallback(
    async (changes: Partial<Profile>) => {
      const profile = await api.put<Profile>("/api/profile", changes);
      setMeState((m) => (m ? { ...m, profile } : m));
      setFeelPrefs({ sounds: profile.sounds, haptics: profile.haptics });
    },
    []
  );

  useEffect(() => {
    Promise.all([refreshMe(), api.get<CatalogMeta>("/api/catalog/meta").then(setMeta).catch(() => {})]).finally(() => setReady(true));
  }, [refreshMe]);

  useEffect(() => {
    if (me) loadPlan();
    else setPlan(null);
  }, [me?.id, loadPlan]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const theme = me?.profile.theme ?? "auto";
    const root = document.documentElement;
    if (theme === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme === "claro" ? "light" : "dark");
  }, [me?.profile.theme]);

  const value = useMemo<Store>(
    () => ({
      me, ready, plan, meta, setMe, refreshMe, setPlan, loadPlan, saveProfile, toast, toasts,
      premiumOpen, openPremium: (open = true) => { if (open) feel("open"); setPremiumOpen(open); },
    }),
    [me, ready, plan, meta, setMe, refreshMe, loadPlan, saveProfile, toast, toasts, premiumOpen]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error("StoreProvider faltante");
  return s;
}
