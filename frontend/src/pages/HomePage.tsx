import { useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useMatchesInWindow, useUpcomingMatches } from "@/hooks/useMatches";
import { useMatchCardSummaries } from "@/hooks/useMatchCardSummary";
import { MatchCard } from "@/components/matches/MatchCard";
import { Button } from "@/components/ui/button";

type DayFilter = { kind: "day"; label: "Hoje" | "Amanhã"; offsetDays: 0 | 1 };
type UpcomingFilter = { kind: "upcoming"; label: "Semana"; days: 7 };
type Filter = DayFilter | UpcomingFilter;

const FILTERS = [
  { kind: "day", label: "Hoje", offsetDays: 0 },
  { kind: "day", label: "Amanhã", offsetDays: 1 },
  { kind: "upcoming", label: "Semana", days: 7 },
] as const satisfies readonly Filter[];

const DEFAULT_FILTER: Filter = FILTERS[0];

function localDayWindow(offsetDays: number): { from: Date; to: Date } {
  const from = new Date();
  from.setDate(from.getDate() + offsetDays);
  from.setHours(0, 0, 0, 0);
  const to = new Date(from);
  to.setHours(23, 59, 59, 999);
  return { from, to };
}

export default function HomePage() {
  const [filter, setFilter] = useState<Filter>(DEFAULT_FILTER);

  const window = useMemo(
    () => (filter.kind === "day" ? localDayWindow(filter.offsetDays) : null),
    [filter],
  );

  const dayQuery = useMatchesInWindow(
    window?.from ?? new Date(0),
    window?.to ?? new Date(0),
    filter.kind === "day",
  );
  const upcomingQuery = useUpcomingMatches(
    filter.kind === "upcoming" ? filter.days : 7,
    filter.kind === "upcoming",
  );

  const active = filter.kind === "day" ? dayQuery : upcomingQuery;
  const data = active.data;
  const isLoading = active.isLoading;
  const isError = active.isError;

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

  const summaries = useMatchCardSummaries(sortedMatches);

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
          Não foi possível carregar os jogos.
        </p>
      )}

      {!isLoading && sortedMatches.length === 0 && (
        <p className="text-fg-muted text-sm py-8 text-center">
          Nenhum jogo nesse intervalo.
        </p>
      )}

      <div className="space-y-3">
        {sortedMatches.map((m) => {
          const s = summaries.get(m.id);
          return (
            <MatchCard
              key={m.id}
              match={m}
              {...(s?.probs ? { probs: s.probs } : {})}
              valueBetsCount={s?.valueBetsCount ?? 0}
            />
          );
        })}
      </div>
    </div>
  );
}
