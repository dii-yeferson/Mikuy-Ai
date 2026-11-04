import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { User } from "./types";

type Context = {
  user: User | null;
  setUser: (u: User | null) => void;
  refresh: () => Promise<void>;
  loading: boolean;
  error: string;
  notify: (s: string, undo?: () => Promise<void>) => void;
};
const AppContext = createContext<Context>(null!);
export const useApp = () => useContext(AppContext);
export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const undo = useRef<(() => Promise<void>) | undefined>(undefined);
  const [undoBusy, setUndoBusy] = useState(false);
  const notify = useCallback((text: string, action?: () => Promise<void>) => {
    undo.current = action;
    setNotice(text);
  }, []);
  const refresh = async () => {
    setUser(await api<User>("/auth/me"));
  };
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch((e) => {
        if (e.status !== 401) setError(e.message);
      })
      .finally(() => setLoading(false));
    const expired = () => {
      undo.current = undefined;
      setUser(null);
      setNotice("Tu sesión expiró. Inicia sesión para continuar.");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  useEffect(() => {
    if (notice) {
      const id = setTimeout(() => setNotice(""), 6500);
      return () => clearTimeout(id);
    }
  }, [notice]);
  return (
    <AppContext.Provider
      value={{ user, setUser, refresh, loading, error, notify }}
    >
      {children}
      <div className="toast" role="status" aria-live="polite">
        {notice}
        {notice && undo.current && (
          <button
            disabled={undoBusy}
            onClick={async () => {
              setUndoBusy(true);
              try {
                await undo.current?.();
                notify("Registro eliminado");
              } catch (e) {
                notify((e as Error).message);
              } finally {
                setUndoBusy(false);
              }
            }}
          >
            Deshacer
          </button>
        )}
      </div>
    </AppContext.Provider>
  );
}
