import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { clearApiKey, getApiKey, setApiKey } from "@/lib/auth";

export const OPEN_API_KEY_DIALOG_EVENT = "open-api-key-dialog";

export function ApiKeyDialog() {
  const [open, setOpen] = useState(() => !getApiKey());
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const hasStoredKey = Boolean(getApiKey());

  useEffect(() => {
    const handler = () => {
      setError(null);
      setValue("");
      setOpen(true);
    };
    window.addEventListener(OPEN_API_KEY_DIALOG_EVENT, handler);
    return () => window.removeEventListener(OPEN_API_KEY_DIALOG_EVENT, handler);
  }, []);

  const save = async () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch("/v1/models", { headers: { "X-API-Key": trimmed } });
      if (res.status === 401 || res.status === 403) {
        setError("Token inválido. Verifique e tente novamente.");
        return;
      }
      if (!res.ok) {
        setError(`Erro ${res.status} ao validar o token.`);
        return;
      }
      setApiKey(trimmed);
      setValue("");
      setOpen(false);
      window.location.reload();
    } catch {
      setError("Falha de rede ao validar o token. Verifique sua conexão.");
    } finally {
      setSubmitting(false);
    }
  };

  const logout = () => {
    clearApiKey();
    window.location.reload();
  };

  // Block close while no valid key is stored — prevents being stranded behind
  // an invalid token with no way back.
  const handleOpenChange = (next: boolean) => {
    if (!next && !hasStoredKey) return;
    setOpen(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>API Key</DialogTitle>
          <DialogDescription>
            Cole sua chave do backend (variável <code>ANALYTIS_API_KEY</code>). Ela fica salva
            só neste navegador.
          </DialogDescription>
        </DialogHeader>
        <Input
          type="password"
          autoFocus
          placeholder="cole seu token"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(null);
          }}
          onKeyDown={(e) => e.key === "Enter" && !submitting && save()}
          disabled={submitting}
          aria-invalid={Boolean(error)}
        />
        {error && (
          <p role="alert" className="text-sm text-red-400">
            {error}
          </p>
        )}
        <div className="flex items-center justify-between gap-2">
          {hasStoredKey ? (
            <Button variant="ghost" onClick={logout} type="button">
              <LogOut className="h-4 w-4 mr-1.5" />
              Sair
            </Button>
          ) : (
            <span />
          )}
          <Button
            variant="gradient"
            onClick={save}
            disabled={!value.trim() || submitting}
          >
            {submitting ? "Validando..." : "Salvar"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
