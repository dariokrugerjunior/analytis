import { cn } from "@/lib/utils";

interface Props {
  home: number;
  draw: number;
  away: number;
  compact?: boolean;
}

export function MarketBars({ home, draw, away, compact = false }: Props) {
  const fmt = (v: number) => `${Math.round(v * 100)}%`;
  return (
    <div className="space-y-1">
      <div className={cn("flex gap-1", compact ? "h-1.5" : "h-2")}>
        <div className="rounded-full gradient-home" style={{ flex: home }} />
        <div className="rounded-full bg-outcome-draw/60" style={{ flex: draw }} />
        <div className="rounded-full gradient-away" style={{ flex: away }} />
      </div>
      <div
        className={cn(
          "flex justify-between text-fg-muted font-mono",
          compact ? "text-[10px]" : "text-xs",
        )}
      >
        <span>{fmt(home)}</span>
        <span>{fmt(draw)}</span>
        <span>{fmt(away)}</span>
      </div>
    </div>
  );
}
