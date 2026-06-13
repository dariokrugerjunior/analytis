import { NavLink } from "react-router-dom";
import { Gem, Home, Settings, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Value Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
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
          onClick={() => alert("Em breve")}
          aria-label="Configurações"
          type="button"
        >
          <Settings className="h-4 w-4" />
        </button>
      </nav>
    </header>
  );
}
