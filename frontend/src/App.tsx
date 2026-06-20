import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import HomePage from "@/pages/HomePage";
import MatchDetailPage from "@/pages/MatchDetailPage";
import ValueBetsPage from "@/pages/ValueBetsPage";
import ClvSummaryPage from "@/pages/ClvSummaryPage";
import MethodologyPage from "@/pages/MethodologyPage";
import NotFoundPage from "@/pages/NotFoundPage";
import { queryClient } from "@/lib/query-client";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ApiKeyDialog />
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/matches/:matchId" element={<MatchDetailPage />} />
            <Route path="/bets" element={<ValueBetsPage />} />
            <Route path="/clv" element={<ClvSummaryPage />} />
            <Route path="/metodologia" element={<MethodologyPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
