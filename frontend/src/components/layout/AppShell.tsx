import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { BottomNav } from "./BottomNav";

export function AppShell() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 mx-auto w-full max-w-3xl px-4 pb-24 md:pb-6 pt-4">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  );
}
