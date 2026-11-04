import { useEffect } from "react";
import { useApp } from "../context";
import { api, today } from "../api";
import { completeProfile } from "../experience";
import type { Profile } from "../types";

export function ExperienceRuntime() {
  const { user, notify } = useApp();
  useEffect(() => {
    let profile: ReturnType<typeof completeProfile> | null = null;
    const seen = new Set<string>();
    const apply = (p: Profile) => {
      profile = completeProfile(p);
      const a = profile.settings.appearance;
      document.documentElement.dataset.appearance =
        a === "Tema del dispositivo"
          ? matchMedia("(prefers-color-scheme: light)").matches
            ? "Claro"
            : "Oscuro"
          : a;
    };
    const update = (e: Event) => apply((e as CustomEvent<Profile>).detail);
    if (user)
      api<Profile>("/profile")
        .then(apply)
        .catch(() => {});
    window.addEventListener("profile-saved", update);
    const timer = setInterval(() => {
      if (!profile || document.visibilityState !== "visible") return;
      const now = new Date(),
        time =
          String(now.getHours()).padStart(2, "0") +
          ":" +
          String(now.getMinutes()).padStart(2, "0"),
        day = (now.getDay() + 6) % 7;
      for (const [name, r] of Object.entries(profile.settings.reminders)) {
        const key = today() + name + time;
        const minutes = now.getHours() * 60 + now.getMinutes(),
          start = Number(r.time.slice(0, 2)) * 60 + Number(r.time.slice(3));
        const due =
          name === "Agua"
            ? minutes >= start &&
              (minutes - start) % (r.interval_hours * 60) === 0
            : r.time === time;
        if (r.enabled && r.days.includes(day) && due && !seen.has(key)) {
          seen.add(key);
          notify("Recordatorio: " + name);
          if (profile.settings.vibration) navigator.vibrate?.(100);
        }
      }
    }, 10000);
    return () => {
      clearInterval(timer);
      window.removeEventListener("profile-saved", update);
      delete document.documentElement.dataset.appearance;
    };
  }, [user?.id, notify]);
  return null;
}
