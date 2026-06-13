import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import HomePage from "@/pages/HomePage";
import MatchDetailPage from "@/pages/MatchDetailPage";
import ValueBetsPage from "@/pages/ValueBetsPage";
import ClvSummaryPage from "@/pages/ClvSummaryPage";
import NotFoundPage from "@/pages/NotFoundPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/matches/:matchId" element={<MatchDetailPage />} />
          <Route path="/bets" element={<ValueBetsPage />} />
          <Route path="/clv" element={<ClvSummaryPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
