import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  enablePush,
  hasBeenAsked,
  isInstalledPwa,
  isPushSupported,
  isSubscribed,
  markAsked,
} from "@/lib/push";

export function PushPrompt() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isPushSupported()) return;
    if (!isInstalledPwa()) return;
    if (hasBeenAsked()) return;
    if (isSubscribed()) return;
    if (Notification.permission !== "default") return;
    setOpen(true);
  }, []);

  const handleAccept = async () => {
    setBusy(true);
    try {
      await enablePush();
    } catch {
      // markAsked already invoked inside push.ts when relevant; swallow
    } finally {
      setBusy(false);
      setOpen(false);
    }
  };

  const handleLater = () => {
    markAsked();
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleLater()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Receber notificações dos jogos?</DialogTitle>
          <DialogDescription>
            Você vai receber um alerta 10 minutos antes de cada partida da Copa
            (com a previsão do modelo) e logo após o apito final (com o resultado
            e se a previsão acertou).
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="ghost" onClick={handleLater} disabled={busy}>
            Mais tarde
          </Button>
          <Button variant="gradient" onClick={handleAccept} disabled={busy}>
            {busy ? "Configurando..." : "Sim, ativar"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
