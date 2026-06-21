import { NavLink } from "react-router-dom";
import { Bell, BookOpen, Gem, Home, Settings, Target, TrendingUp } from "lucide-react";
import { OPEN_API_KEY_DIALOG_EVENT } from "@/components/ApiKeyDialog";
import { enablePush } from "@/lib/push";
import { cn } from "@/lib/utils";

async function handlePushClick() {
  try {
    await enablePush();
    alert("Notificações ativadas com sucesso!");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    alert(`Falha ao ativar notificações: ${msg}`);
  }
}

const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Value Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
  { to: "/acertos", label: "Acertos", icon: Target },
  { to: "/metodologia", label: "Metodologia", icon: BookOpen },
];

export function Header() {
  return (
    <header className="hidden md:flex sticky top-0 z-20 items-center justify-between px-6 py-3 border-b border-white/10 bg-bg-base/80 backdrop-blur">
      <NavLink to="/" className="font-bold text-xl tracking-wide text-gradient-brand">
        ANALYTIS
      </NavLink>
      <nav className="flex items-center gap-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
                isActive ? "bg-bg-overlay text-fg-primary" : "text-fg-muted hover:text-fg-primary",
              )
            }
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </NavLink>
        ))}
        <button
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-fg-muted hover:text-fg-primary"
          onClick={handlePushClick}
          aria-label="Ativar notificações"
          type="button"
        >
          <Bell className="h-4 w-4" />
        </button>
        <button
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-fg-muted hover:text-fg-primary"
          onClick={() => window.dispatchEvent(new Event(OPEN_API_KEY_DIALOG_EVENT))}
          aria-label="Configurações"
          type="button"
        >
          <Settings className="h-4 w-4" />
        </button>
      </nav>
    </header>
  );
}
