import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string;
  subtext?: string;
  colorClass?: string;
}

export function KpiCard({ label, value, subtext, colorClass }: Props) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-fg-muted">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold", colorClass ?? "text-fg-primary")}>
        {value}
      </p>
      {subtext && <p className="text-xs text-fg-muted">{subtext}</p>}
    </Card>
  );
}
