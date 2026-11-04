import { X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { feel } from "../lib/feel";

interface Props {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  hideClose?: boolean;
}

/** Hoja inferior de vidrio: se abre con resorte y se cierra deslizando hacia abajo o tocando fuera. */
export default function Sheet({ open, onClose, title, children, actions, hideClose }: Props) {
  const [mounted, setMounted] = useState(open);
  const [leaving, setLeaving] = useState(false);
  const sheet = useRef<HTMLDivElement>(null);
  const drag = useRef<{ y: number; dy: number } | null>(null);

  useEffect(() => {
    if (open) {
      setMounted(true);
      setLeaving(false);
      feel("open");
    } else if (mounted) {
      setLeaving(true);
      const t = setTimeout(() => setMounted(false), 260);
      return () => clearTimeout(t);
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!mounted) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [mounted]); // eslint-disable-line react-hooks/exhaustive-deps

  function close() {
    feel("close");
    onClose();
  }

  function onDown(e: React.PointerEvent) {
    drag.current = { y: e.clientY, dy: 0 };
    (e.target as Element).setPointerCapture?.(e.pointerId);
  }
  function onMove(e: React.PointerEvent) {
    if (!drag.current || !sheet.current) return;
    const dy = Math.max(0, e.clientY - drag.current.y);
    drag.current.dy = dy;
    sheet.current.style.transition = "none";
    sheet.current.style.transform = `translate(-50%, ${dy}px)`;
  }
  function onUp() {
    if (!drag.current || !sheet.current) return;
    const { dy } = drag.current;
    drag.current = null;
    sheet.current.style.transition = "transform .35s cubic-bezier(.22,1,.36,1)";
    if (dy > 110) close();
    else sheet.current.style.transform = "translate(-50%, 0)";
  }

  if (!mounted) return null;
  return createPortal(
    <>
      <div className={`scrim ${leaving ? "leaving" : ""}`} onClick={close} />
      <div ref={sheet} className={`sheet glass ${leaving ? "leaving" : ""}`} role="dialog" aria-modal="true">
        <div className="sheet-grab" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
          <span />
        </div>
        {(title || !hideClose) && (
          <div className="sheet-head" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp}>
            <h2>{title}</h2>
            <div className="row">
              {actions}
              {!hideClose && (
                <button className="icon-btn" aria-label="Cerrar" onClick={close}>
                  <X size={20} />
                </button>
              )}
            </div>
          </div>
        )}
        <div className="sheet-body">{children}</div>
      </div>
    </>,
    document.body
  );
}
