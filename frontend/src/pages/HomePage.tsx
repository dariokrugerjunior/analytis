import { useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { MatchCard } from "@/components/matches/MatchCard";
import { Button } from "@/components/ui/button";

const FILTERS = [
  { label: "Hoje", days: 1 },
  { label: "Amanhã", days: 2 },
  { label: "Semana", days: 7 },
] as const;

export default function HomePage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>(FILTERS[0]);
  const { data, isLoading, isError } = useUpcomingMatches(filter.days);

  const sortedMatches = useMemo(
    () =>
      data?.items
        .slice()
        .sort(
          (a, b) =>
            new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime(),
        ) ?? [],
    [data],
  );

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Jogos</h2>
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={filter.label === f.label ? "gradient" : "ghost"}
              size="sm"
              onClick={() => setFilter(f)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </header>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-brand-danger">
          Não foi possível carregar os jogos. Verifique se o backend está online.
        </p>
      )}

      {!isLoading && sortedMatches.length === 0 && (
        <p className="text-fg-muted text-sm py-8 text-center">
          Nenhum jogo nesse intervalo. Tente ampliar pra "Semana".
        </p>
      )}

      <div className="space-y-3">
        {sortedMatches.map((m) => (
          <MatchCard key={m.id} match={m} />
        ))}
      </div>
    </div>
  );
}
