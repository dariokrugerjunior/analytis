import type { OddsResponse } from "@/lib/api";

interface Props {
  matchId: string;
  odds: OddsResponse | undefined;
  isLoading: boolean;
}

export function OddsTab({ odds, isLoading }: Props) {
  if (isLoading) return <p className="text-fg-muted text-sm">Carregando odds...</p>;
  if (!odds || odds.quotes.length === 0) {
    return <p className="text-fg-muted text-sm">Nenhuma odd disponível.</p>;
  }
  return (
    <div className="text-fg-muted text-sm">
      {odds.quotes.length} quote(s) — detalhe em breve (Task 13).
    </div>
  );
}
