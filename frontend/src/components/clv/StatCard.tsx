import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

interface Props {
  label: string;
  value: string;
  hint?: string;
  variant?: "default" | "positive" | "negative";
}

export function StatCard({ label, value, hint, variant = "default" }: Props) {
  const valueClass =
    variant === "positive"
      ? "text-brand-primary"
      : variant === "negative"
      ? "text-brand-danger"
      : "text-fg-primary";
  return (
    <Card className="p-4 flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wide text-fg-muted">
        {label}
      </span>
      <span className={cn("font-mono text-2xl font-semibold", valueClass)}>
        {value}
      </span>
      {hint && <span className="text-[11px] text-fg-subtle">{hint}</span>}
    </Card>
  );
}
