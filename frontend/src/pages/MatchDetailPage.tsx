import { useParams } from "react-router-dom";

export default function MatchDetailPage() {
  const { matchId } = useParams();
  return <h2 className="text-2xl font-semibold">Match: {matchId}</h2>;
}
