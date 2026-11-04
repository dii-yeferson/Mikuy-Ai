import { Check, Info, MapPin, Share2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { TopBar } from "../components/Chrome";
import { api, soles } from "../lib/api";
import { feel } from "../lib/feel";
import { useStore } from "../lib/store";
import type { Shopping as Shop } from "../lib/types";

export default function Shopping() {
  const { plan, meta, me, toast } = useStore();
  const [shop, setShop] = useState<Shop | null | undefined>(undefined);
  const load = useCallback(() => api.get<{ shopping: Shop | null }>("/api/shopping").then((r) => setShop(r.shopping)), []);
  useEffect(() => {
    load();
  }, [load, plan?.version, plan?.id]);

  async function toggle(id: string, checked: boolean) {
    feel(checked ? "check" : "uncheck");
    setShop((s) => s && { ...s, sections: s.sections.map((sec) => ({ ...sec, items: sec.items.map((i) => (i.id === id ? { ...i, checked } : i)) })) });
    try {
      const r = await api.post<{ shopping: Shop }>("/api/shopping/check", { id, checked });
      setShop(r.shopping);
      if (checked && r.shopping.pending === 0) {
        feel("celebrate");
        toast("¡Compraste todo! 🛒✨");
      }
    } catch (e) {
      toast((e as Error).message, "error");
      load();
    }
  }

  async function pantry(on: boolean) {
    feel(on ? "toggleOn" : "toggleOff");
    const r = await api.post<{ shopping: Shop }>("/api/shopping/pantry", { include_pantry: on });
    setShop(r.shopping);
  }

  async function share() {
    if (!shop) return;
    feel("tap");
    const text = shop.text;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Lista de compras Mikuy", text });
        return;
      } catch {
        /* cancelado */
      }
    }
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
  }

  const city = meta?.cities.find((c) => c.id === me?.profile.city)?.name ?? "Lima";
  const done = shop ? shop.sections.reduce((a, s) => a + s.items.filter((i) => !i.hidden && i.checked).length, 0) : 0;
  return (
    <>
      <TopBar sub={<span className="row" style={{ gap: 4 }}><MapPin size={13} /> Precios aprox. en {city}</span>} title="Compras" right={shop && <button className="icon-btn" aria-label="Compartir" onClick={share}><Share2 size={18} /></button>} />
      <div className="page stack">
        {shop === undefined ? (
          <div className="skeleton" style={{ height: 300 }} />
        ) : shop === null ? (
          <div className="empty"><div className="big">🛒</div><div className="muted">Crea tu menú y aquí aparecerá tu lista consolidada.</div></div>
        ) : (
          <>
            <div className="card glow stack" style={{ gap: 8 }}>
              <div className="between">
                <div>
                  <div className="tiny muted bold">EN EL MERCADO (APROX.)</div>
                  <div style={{ fontSize: 30, fontWeight: 1000 }}>{soles(shop.total_buy)}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="tiny muted bold">FALTA COMPRAR</div>
                  <div className="bold gold" style={{ fontSize: 20 }}>{soles(shop.pending)}</div>
                </div>
              </div>
              <div className="meter"><i style={{ width: `${shop.count ? (done / shop.count) * 100 : 0}%` }} /></div>
              <div className="small muted">
                {done} de {shop.count} productos · para {shop.people} {shop.people === 1 ? "persona" : "personas"}
              </div>
              <div className="small">
                Esta semana cocinas <b className="gold">{soles(shop.total_used)}</b>
                {shop.total_buy - shop.total_used > 1 && <> · lo demás (<b>{soles(shop.total_buy - shop.total_used)}</b>) queda en tu despensa para otras semanas</>}
              </div>
            </div>
            <button className="card between" onClick={() => pantry(!shop.include_pantry)} style={{ textAlign: "left" }}>
              <div>
                <div className="bold">Incluir despensa</div>
                <div className="small muted">Sal, aceite, especias, azúcar y sillao</div>
              </div>
              <span className={`switch ${shop.include_pantry ? "on" : ""}`} />
            </button>
            {shop.sections.map((sec) => {
              const items = sec.items.filter((i) => !i.hidden);
              if (!items.length) return null;
              return (
                <div key={sec.id}>
                  <div className="section-title" style={{ marginTop: 8 }}>{sec.name}<small>{items.filter((i) => i.checked).length}/{items.length}</small></div>
                  <div className="list">
                    {items.map((i) => (
                      <button key={i.id} className={`shop-row ${i.checked ? "done" : ""}`} onClick={() => toggle(i.id, !i.checked)}>
                        <span className={`check ${i.checked ? "on" : ""}`}>{i.checked && <Check size={16} strokeWidth={3} />}</span>
                        <div className="grow">
                          <div className="bold name">{i.name}</div>
                          <div className="tiny muted ellipsis">Compra {i.buy} · usas {i.need}</div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div className="bold">{soles(i.buy_cost)}</div>
                          <div className="tiny faint">{soles(i.unit_price)}/{i.price_unit}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
            <div className="notice"><Info size={18} /><span>{meta?.price_note} Actualizado: {meta?.price_date}.</span></div>
          </>
        )}
      </div>
    </>
  );
}
