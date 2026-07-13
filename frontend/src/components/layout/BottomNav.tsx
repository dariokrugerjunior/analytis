import { NavLink } from "react-router-dom";
import { Bell, BookOpen, CalendarDays, LayoutDashboard, Target } from "lucide-react";
import { enablePush } from "@/lib/push";
import { cn } from "@/lib/utils";

async function handlePushClick() {
  try {
    await enablePush();
    alert("Notificações ativadas!");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    alert(`Falha: ${msg}`);
  }
}

const navItems = [
  { to: "/", label: "Painel", icon: LayoutDashboard },
  { to: "/jogos", label: "Jogos", icon: CalendarDays },
  { to: "/acertos", label: "Acertos", icon: Target },
  { to: "/metodologia", label: "Metodo", icon: BookOpen },
];

export function BottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 grid grid-cols-5 border-t border-white/10 bg-bg-base/90 backdrop-blur pb-[env(safe-area-inset-bottom)]">
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
        onClick={handlePushClick}
        aria-label="Ativar notificações"
        type="button"
      >
        <Bell className="h-5 w-5" />
        <span>Push</span>
      </button>
    </nav>
  );
}
