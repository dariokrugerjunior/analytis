import { Gem } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { ValueBet } from "@/lib/api";

interface Props {
  bet: ValueBet;
  showMatchLink?: boolean;
  matchLabel?: string;
}

const OUTCOME_LABELS: Record<string, string> = {
  home: "Mandante vence",
  draw: "Empate",
  away: "Visitante vence",
  "over_2.5": "Over 2.5 gols",
  "under_2.5": "Under 2.5 gols",
  yes: "BTTS Sim",
  no: "BTTS Não",
};

const MARKET_LABELS: Record<string, string> = {
  "1x2": "1X2",
  over_under_goals: "OU 2.5",
  btts: "BTTS",
};

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function edgeColorClass(edge: number): string {
  if (edge >= 0.1) return "from-emerald-400 to-emerald-600";
  if (edge >= 0.03) return "from-amber-400 to-amber-600";
  return "from-slate-400 to-slate-600";
}

export function ValueBetCard({ bet, showMatchLink, matchLabel }: Props) {
  const outcomeLabel = OUTCOME_LABELS[bet.outcome] ?? bet.outcome;
  const marketLabel = MARKET_LABELS[bet.market] ?? bet.market;

  return (
    <Card className="overflow-hidden">
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          {showMatchLink && matchLabel && (
            <span className="text-[11px] uppercase tracking-wide text-fg-muted">
              {matchLabel}
            </span>
          )}
          <span className="text-sm font-semibold">
            {marketLabel} · <span className="text-fg-primary">{outcomeLabel}</span>
          </span>
        </div>
        <Badge variant="edge" className="inline-flex items-center gap-1">
          <Gem className="h-3 w-3" />
          +{(bet.edge * 100).toFixed(1)}%
        </Badge>
      </div>
      <div className="px-4 py-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-[11px] uppercase text-fg-muted">Casa</div>
          <div className="font-medium">{bet.bookmaker}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase text-fg-muted">Odds</div>
          <div className="font-mono">{bet.decimal_odds.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase text-fg-muted">Nossa prob</div>
          <div className="font-mono">{fmtPct(bet.our_prob)}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase text-fg-muted">Mercado</div>
          <div className="font-mono">{fmtPct(bet.market_prob)}</div>
        </div>
      </div>
      <div className="px-4 py-3 border-t border-white/10 grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-[11px] uppercase text-fg-muted">Kelly (1/4)</div>
          <div className="font-mono">{(bet.kelly_fraction * 100).toFixed(2)}%</div>
        </div>
        <div>
          <div className="text-[11px] uppercase text-fg-muted">Stake sugerido</div>
          <div className={`font-mono font-bold bg-gradient-to-r bg-clip-text text-transparent ${edgeColorClass(bet.edge)}`}>
            {bet.suggested_stake_units.toFixed(1)}u
          </div>
        </div>
      </div>
      {bet.closing_clv !== null && (
        <div className="px-4 py-2 border-t border-white/10 text-[11px] text-fg-muted">
          CLV: <span className="font-mono">{(bet.closing_clv * 100).toFixed(2)}%</span>
          {bet.closing_decimal_odds !== null && (
            <span> · Fechou em {bet.closing_decimal_odds.toFixed(2)}</span>
          )}
        </div>
      )}
    </Card>
  );
}
