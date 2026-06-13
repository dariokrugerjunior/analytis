import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { getApiKey, setApiKey } from "@/lib/auth";

interface Props {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function ApiKeyDialog({ open: controlledOpen, onOpenChange }: Props) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [value, setValue] = useState("");

  useEffect(() => {
    if (controlledOpen === undefined && !getApiKey()) {
      setInternalOpen(true);
    }
  }, [controlledOpen]);

  const open = controlledOpen ?? internalOpen;
  const setOpen = (next: boolean) => {
    if (onOpenChange) onOpenChange(next);
    else setInternalOpen(next);
  };

  const save = () => {
    setApiKey(value);
    setValue("");
    setOpen(false);
    window.location.reload();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
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
          placeholder="local-dev-change-me"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save()}
        />
        <Button variant="gradient" onClick={save} disabled={!value.trim()}>
          Salvar
        </Button>
      </DialogContent>
    </Dialog>
  );
}
