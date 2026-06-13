import { Skeleton } from "@/components/ui/skeleton";
import { ValueBetCard } from "@/components/bets/ValueBetCard";
import type { ValueBetsList } from "@/lib/api";

interface Props {
  matchId: string;
  valueBets: ValueBetsList | undefined;
  isLoading: boolean;
}

export function ValueBetsTab({ valueBets, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    );
  }
  if (!valueBets || valueBets.items.length === 0) {
    return (
      <p className="text-fg-muted text-sm py-8 text-center">
        Nenhum value bet encontrado.
        <br />
        Rode <code>analytis bets find-value --match-id ... --model ...</code> primeiro.
      </p>
    );
  }

  const sorted = [...valueBets.items].sort((a, b) => b.edge - a.edge);

  return (
    <div className="space-y-3 pb-6">
      {sorted.map((bet) => (
        <ValueBetCard key={bet.id} bet={bet} />
      ))}
    </div>
  );
}
