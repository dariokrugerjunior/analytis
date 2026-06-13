import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function App() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-3xl font-bold text-gradient-brand">analytis</h1>
      <p className="text-fg-muted">Plano 4 — frontend live</p>
      <div className="flex gap-2">
        <Button variant="default">Default</Button>
        <Button variant="gradient">Value bet</Button>
        <Button variant="outline">Ghost</Button>
      </div>
      <div className="flex gap-2">
        <Badge variant="edge">+23% edge</Badge>
        <Badge variant="live">LIVE</Badge>
        <Badge variant="outcomeHome">HOME</Badge>
      </div>
    </main>
  );
}
