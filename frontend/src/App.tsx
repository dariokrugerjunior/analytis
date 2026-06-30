import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import { PushPrompt } from "@/components/PushPrompt";
import HomePage from "@/pages/HomePage";
import MatchDetailPage from "@/pages/MatchDetailPage";
import AccuracyPage from "@/pages/AccuracyPage";
import MethodologyPage from "@/pages/MethodologyPage";
import NotFoundPage from "@/pages/NotFoundPage";
import { queryClient } from "@/lib/query-client";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ApiKeyDialog />
        <PushPrompt />
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/matches/:matchId" element={<MatchDetailPage />} />
            <Route path="/acertos" element={<AccuracyPage />} />
            <Route path="/metodologia" element={<MethodologyPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
