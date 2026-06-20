import type { ModelOption } from "@/lib/api";

interface Props {
  models: ModelOption[];
  selected: string;
  onChange: (name: string) => void;
}

export function ModelSelector({ models, selected, onChange }: Props) {
  return (
    <select
      value={selected}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-white/10 bg-bg-elevated px-3 py-2 text-sm text-fg-primary focus:outline-none focus:ring-2 focus:ring-fg-primary/20"
    >
      {models.map((m) => (
        <option key={m.id} value={m.name}>
          {m.name} ({m.n_predictions} jogos)
        </option>
      ))}
    </select>
  );
}
