import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiCard } from "@/components/accuracy/KpiCard";
import { DashboardScoreChart } from "@/components/dashboard/DashboardScoreChart";
import { useDashboardScores } from "@/hooks/useDashboardScores";
import type { DashboardGame, Outcome } from "@/lib/api";
import { CANONICAL_MODEL } from "@/lib/models";
import { cn } from "@/lib/utils";

const OUTCOME_LABELS: Record<Outcome, string> = {
  home: "Casa",
  draw: "Empate",
  away: "Fora",
};

function avgColor(avg: number): string {
  if (avg >= 60) return "text-green-400";
  if (avg >= 30) return "text-yellow-400";
  return "text-red-400";
}

function pointsBadgeClass(points: number): string {
  if (points >= 100) return "bg-green-500/15 text-green-300";
  if (points >= 50) return "bg-yellow-500/15 text-yellow-300";
  return "bg-red-500/15 text-red-300";
}

function GameCard({ game }: { game: DashboardGame }) {
  const navigate = useNavigate();
  const outcomeHit = game.outcome_predicted === game.outcome_actual;
  return (
    <Card
      className="p-3 cursor-pointer hover:bg-bg-overlay/40 transition-colors"
      onClick={() => navigate(`/matches/${game.match_id}`)}
    >
      <div className="flex justify-between items-center text-xs text-fg-muted mb-1">
        <span>
          {new Date(game.kickoff_utc).toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
          })}
        </span>
        <span
          className={cn(
            "rounded-md px-2 py-0.5 text-xs font-semibold",
            pointsBadgeClass(game.points),
          )}
        >
          {game.points} pts
        </span>
      </div>
      <div className="flex justify-between items-baseline gap-3">
        <span className="text-sm text-fg-primary truncate">
          {game.home_team} vs {game.away_team}
        </span>
        <div className="flex items-baseline gap-2 shrink-0 font-mono text-sm">
          <span className="text-fg-muted">prev {game.predicted_score}</span>
          <span className="text-fg-subtle">→</span>
          <span className="font-semibold text-fg-primary">{game.actual_score}</span>
        </div>
      </div>
      <div className="mt-1 text-xs">
        <span className={outcomeHit ? "text-green-400" : "text-red-400"}>
          {outcomeHit ? "✓" : "✗"} Resultado: {OUTCOME_LABELS[game.outcome_predicted]}
        </span>
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, isLoading, isError, error, refetch } = useDashboardScores(CANONICAL_MODEL);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-3xl">
        <header>
          <h2 className="text-2xl font-semibold">Dashboard</h2>
        </header>
        <Skeleton className="h-24" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-60" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <Card className="p-4">
          <p className="text-sm text-red-400">
            Erro ao carregar: {error instanceof Error ? error.message : "desconhecido"}
          </p>
          <button
            type="button"
            className="mt-2 text-sm underline text-fg-primary"
            onClick={() => refetch()}
          >
            Tentar novamente
          </button>
        </Card>
      </div>
    );
  }

  const { aggregate, games } = data;

  if (aggregate.total_games === 0) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <Card className="p-6 text-center">
          <p className="text-sm text-fg-muted">
            Nenhum jogo com resultado disponível pra esse modelo ainda.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-fg-muted">
          Pontuação do modelo{" "}
          <span className="text-fg-primary font-medium">{data.model.name}</span> por jogo:{" "}
          <span className="text-green-400">100</span> placar exato,{" "}
          <span className="text-yellow-400">50</span> resultado certo,{" "}
          <span className="text-red-400">0</span> errou.
        </p>
      </header>

      <Card className="p-4">
        <p className="text-xs uppercase tracking-wide text-fg-muted">Pontuação média</p>
        <p className={cn("mt-1 text-4xl font-bold", avgColor(aggregate.avg_points))}>
          {aggregate.avg_points.toFixed(1)}
          <span className="text-lg text-fg-muted font-normal"> / 100</span>
        </p>
        <p className="text-xs text-fg-muted mt-1">
          {aggregate.total_games} jogos avaliados
        </p>
      </Card>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard
          label="Placar exato"
          value={String(aggregate.exact)}
          colorClass="text-green-400"
          subtext="100 pts"
        />
        <KpiCard
          label="Resultado certo"
          value={String(aggregate.outcome_only)}
          colorClass="text-yellow-400"
          subtext="50 pts"
        />
        <KpiCard
          label="Erros"
          value={String(aggregate.missed)}
          colorClass="text-red-400"
          subtext="0 pts"
        />
        <KpiCard label="Total de jogos" value={String(aggregate.total_games)} />
      </div>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-fg-muted mb-1">Pontos por jogo</h3>
        <p className="text-xs text-fg-muted mb-3">
          Cada barra é um jogo (0–100). Verde = placar exato, amarelo = resultado certo,
          vermelho = errou.
        </p>
        <DashboardScoreChart games={games} />
      </Card>

      <section>
        <h3 className="text-base font-semibold mb-2">
          Jogos <span className="text-sm font-normal text-fg-muted">({games.length})</span>
        </h3>
        <div className="space-y-2">
          {games
            .slice()
            .sort(
              (a, b) =>
                new Date(b.kickoff_utc).getTime() - new Date(a.kickoff_utc).getTime(),
            )
            .map((g) => (
              <GameCard key={g.match_id} game={g} />
            ))}
        </div>
      </section>
    </div>
  );
}
