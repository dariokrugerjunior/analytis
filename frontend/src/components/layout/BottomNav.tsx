import { NavLink } from "react-router-dom";
import { BookOpen, Gem, Home, Settings, Target, TrendingUp } from "lucide-react";
import { OPEN_API_KEY_DIALOG_EVENT } from "@/components/ApiKeyDialog";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
  { to: "/acertos", label: "Acertos", icon: Target },
  { to: "/metodologia", label: "Metodo", icon: BookOpen },
];

export function BottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 grid grid-cols-6 border-t border-white/10 bg-bg-base/90 backdrop-blur pb-[env(safe-area-inset-bottom)]">
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            cn(
              "flex flex-col items-center justify-center gap-1 py-3 text-[10px] uppercase tracking-wide transition-colors",
              isActive ? "text-fg-primary" : "text-fg-muted",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon className="h-5 w-5" />
              <span>{label}</span>
              {isActive && <span className="h-0.5 w-6 gradient-edge rounded-full" />}
            </>
          )}
        </NavLink>
      ))}
      <button
        className="flex flex-col items-center justify-center gap-1 py-3 text-[10px] uppercase tracking-wide text-fg-muted"
        onClick={() => window.dispatchEvent(new Event(OPEN_API_KEY_DIALOG_EVENT))}
        aria-label="Configurações"
        type="button"
      >
        <Settings className="h-5 w-5" />
        <span>Config</span>
      </button>
    </nav>
  );
}
