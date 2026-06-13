import type { ValueBetsList } from "@/lib/api";

interface Props {
  matchId: string;
  valueBets: ValueBetsList | undefined;
  isLoading: boolean;
}

export function ValueBetsTab({ valueBets, isLoading }: Props) {
  if (isLoading) return <p className="text-fg-muted text-sm">Carregando bets...</p>;
  if (!valueBets || valueBets.items.length === 0) {
    return <p className="text-fg-muted text-sm">Nenhum value bet encontrado.</p>;
  }
  return (
    <div className="text-fg-muted text-sm">
      {valueBets.items.length} bet(s) — detalhe em breve (Task 14).
    </div>
  );
}
