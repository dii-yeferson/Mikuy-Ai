import type { ReactNode } from "react";

export default function Ring({ value, max, size = 132, stroke = 12, children }: { value: number; max: number; size?: number; stroke?: number; children?: ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, max ? value / max : 0));
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <defs>
          <linearGradient id="goldGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#ffe27a" />
            <stop offset="60%" stopColor="#f6b53a" />
            <stop offset="100%" stopColor="#e8891f" />
          </linearGradient>
        </defs>
        <circle className="track" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} />
        <circle className="bar" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
      </svg>
      <div className="label">{children}</div>
    </div>
  );
}
