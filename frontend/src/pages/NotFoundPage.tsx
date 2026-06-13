import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center gap-4 py-16">
      <h2 className="text-2xl font-semibold">404</h2>
      <p className="text-fg-muted">Página não encontrada.</p>
      <Button asChild>
        <Link to="/">Voltar pra Home</Link>
      </Button>
    </div>
  );
}
