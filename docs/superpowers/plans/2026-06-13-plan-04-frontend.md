# Plano 4 — Frontend Vibrant Sportbook

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o frontend React mobile-first (estilo Vibrant Sportbook) servido pelo próprio FastAPI em `http://localhost:8000/`, expondo 4 telas (Home / Match Detail / Value Bets / CLV Summary) que consomem a API existente sem dependências externas adicionais.

**Architecture:** Pasta `frontend/` em monorepo, Vite + React 18 + TypeScript strict + Tailwind CSS (tokens Vibrant) + shadcn/ui + TanStack Query + React Router v6 + Recharts. API key fica em `localStorage`, modal pede no primeiro acesso. Em produção, `pnpm build` gera `frontend/dist/` que FastAPI serve como static files; backend ganha uma rota nova (`GET /v1/matches?upcoming=true&days=N`) e nova CLI (`analytis frontend build/dev`). Sem SSR, sem framework full-stack.

**Tech Stack:** Vite 5, React 18, TypeScript 5.6 (strict), Tailwind CSS 3.4, shadcn/ui, TanStack Query 5, React Router v6, Recharts 2, Vitest, React Testing Library, ESLint, Prettier, pnpm 9. Backend Python existente (FastAPI/SQLAlchemy/uv).

**Branch:** trabalhar direto em `main` (preferência do usuário desde Plano 2).

**Spec:** `docs/superpowers/specs/2026-06-13-frontend-design.md`.

---

## Estrutura de arquivos do plano

```
analytis/
├── frontend/                                  # NEW (toda a parte web)
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── components.json
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── .gitignore
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── styles/
│       │   └── globals.css
│       ├── lib/
│       │   ├── api.ts
│       │   ├── query-client.ts
│       │   ├── auth.ts
│       │   └── utils.ts
│       ├── components/
│       │   ├── ui/                            # primitives shadcn
│       │   ├── ApiKeyDialog.tsx
│       │   ├── ErrorBoundary.tsx
│       │   ├── layout/
│       │   │   ├── AppShell.tsx
│       │   │   ├── Header.tsx
│       │   │   └── BottomNav.tsx
│       │   ├── matches/
│       │   │   ├── MatchCard.tsx
│       │   │   ├── MarketBars.tsx
│       │   │   ├── ScoreHeatmap.tsx
│       │   │   └── OddsTable.tsx
│       │   ├── bets/
│       │   │   └── ValueBetCard.tsx
│       │   └── clv/
│       │       ├── StatCard.tsx
│       │       └── CLVChart.tsx
│       ├── hooks/
│       │   ├── useMatches.ts
│       │   ├── useMatchPredictions.ts
│       │   ├── useMatchOdds.ts
│       │   ├── useMatchValueBets.ts
│       │   └── useClvSummary.ts
│       └── pages/
│           ├── HomePage.tsx
│           ├── MatchDetailPage.tsx
│           ├── ValueBetsPage.tsx
│           ├── ClvSummaryPage.tsx
│           └── NotFoundPage.tsx
├── src/analytis/
│   ├── api/routes/
│   │   └── matches.py                         # NEW (upcoming list)
│   ├── api/main.py                            # MODIFY (mount static)
│   └── cli/
│       └── frontend.py                        # NEW (build/dev)
└── docs/superpowers/specs/2026-06-13-frontend-design.md
```

---

## Convenções (válidas em todas as tasks)

- **Diretório de trabalho:** `C:\Projetos\Pessoal\analytis`. Quando estiver no Windows e for executar comandos do frontend, todos os comandos `pnpm` rodam dentro de `C:\Projetos\Pessoal\analytis\frontend\`.
- **Branch:** sempre `main`. Sandbox bloqueia commits diretos a `main` pra subagents — **subagents stage apenas e o parent faz o commit**.
- **TDD:** unit tests para `lib/api.ts`, `lib/auth.ts`, hooks, e funções puras (helpers). Smoke tests para Pages com `render` do RTL. Componentes visuais sem lógica não exigem TDD.
- **Mensagens de commit:** inglês, formato `<type>(scope): <message>` (`feat`, `chore`, `fix`, `docs`, `test`, `refactor`). Scope `frontend` para mudanças na nova pasta; sem scope para mudanças no backend.
- **NÃO** adicionar trailer `Co-Authored-By: Claude...`.
- **pnpm path:** se `pnpm` não estiver instalado, instale via `npm install -g pnpm` (precisa do Node.js ≥ 20 já presente — verificar com `node --version`).
- **uv path para os comandos backend (mantido dos planos anteriores):**
  ```bash
  export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
  ```
- **Postgres:** continua rodando em `localhost:5434` (Plano 1). Backend env vars idem:
  ```bash
  export ANALYTIS_DATABASE_URL="postgresql+psycopg://analytis:analytis_dev@localhost:5434/analytis"
  export ANALYTIS_API_KEY="local-dev-change-me"
  ```

---

## Task 1: Bootstrap projeto frontend (pnpm + Vite + React + TypeScript)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/pnpm-workspace.yaml` (opcional, mas ajuda na isolação)
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/.gitignore`

- [ ] **Step 1: Verificar Node.js e instalar pnpm se faltar**

```bash
node --version       # esperar v20+
npm --version        # esperar 10+
pnpm --version || npm install -g pnpm@9
```

Caso `node` esteja ausente, parar e reportar BLOCKED (instalar Node.js LTS via winget: `winget install --id=OpenJS.NodeJS.LTS -e`).

- [ ] **Step 2: Criar `frontend/package.json`**

```json
{
  "name": "analytis-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write src",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-query": "^5.59.0",
    "recharts": "^2.13.0",
    "lucide-react": "^0.453.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4",
    "class-variance-authority": "^0.7.0"
  },
  "devDependencies": {
    "@types/node": "^22.7.5",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "vite": "^5.4.8",
    "typescript": "^5.6.2",
    "tailwindcss": "^3.4.13",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20",
    "@tailwindcss/typography": "^0.5.15",
    "eslint": "^8.57.1",
    "@typescript-eslint/parser": "^8.8.1",
    "@typescript-eslint/eslint-plugin": "^8.8.1",
    "eslint-plugin-react": "^7.37.1",
    "eslint-plugin-react-hooks": "^4.6.2",
    "eslint-plugin-jsx-a11y": "^6.10.0",
    "prettier": "^3.3.3",
    "vitest": "^2.1.2",
    "@vitest/ui": "^2.1.2",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/user-event": "^14.5.2",
    "jsdom": "^25.0.1",
    "@types/testing-library__jest-dom": "^6.0.0"
  }
}
```

- [ ] **Step 3: Criar `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Criar `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Criar `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    target: "es2022",
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

- [ ] **Step 6: Criar `frontend/index.html`**

```html
<!doctype html>
<html lang="pt-BR" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta name="theme-color" content="#0f172a" />
    <title>analytis</title>
  </head>
  <body class="bg-bg-base text-fg-primary antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Criar `frontend/src/main.tsx` placeholder**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 8: Criar `frontend/src/App.tsx` placeholder**

```tsx
export default function App() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <h1 className="text-3xl font-bold">analytis · bootstrap ok</h1>
    </main>
  );
}
```

- [ ] **Step 9: Criar `frontend/.gitignore`**

```
node_modules/
dist/
*.log
.vite/
```

- [ ] **Step 10: Instalar deps e validar build**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm install
pnpm typecheck
```

Expected: pnpm install completa (~30s primeira vez), typecheck passa.

- [ ] **Step 11: Stage (DO NOT commit)**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/package.json frontend/pnpm-lock.yaml frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/.gitignore
git status
```

---

## Task 2: Tailwind + tokens Vibrant + globals.css

**Files:**
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/styles/globals.css`

- [ ] **Step 1: Criar `frontend/postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 2: Criar `frontend/tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "768px",
      },
    },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          base: "#0f172a",
          elevated: "#1e1b4b",
          overlay: "rgba(255,255,255,0.05)",
        },
        fg: {
          primary: "#f1f5f9",
          muted: "#94a3b8",
          subtle: "#475569",
        },
        brand: {
          primary: "#10b981",
          accent: "#fbbf24",
          danger: "#ef4444",
        },
        outcome: {
          home: "#10b981",
          draw: "#9ca3af",
          away: "#ef4444",
        },
        edge: {
          high: "#10b981",
          medium: "#fbbf24",
          low: "#94a3b8",
        },
        // shadcn defaults para integração com primitives
        border: "rgba(255,255,255,0.08)",
        input: "rgba(255,255,255,0.06)",
        ring: "#fbbf24",
        background: "#0f172a",
        foreground: "#f1f5f9",
        primary: {
          DEFAULT: "#10b981",
          foreground: "#0f172a",
        },
        secondary: {
          DEFAULT: "#1e1b4b",
          foreground: "#f1f5f9",
        },
        muted: {
          DEFAULT: "#1e293b",
          foreground: "#94a3b8",
        },
        accent: {
          DEFAULT: "#fbbf24",
          foreground: "#451a03",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#f1f5f9",
        },
        card: {
          DEFAULT: "#1e1b4b",
          foreground: "#f1f5f9",
        },
        popover: {
          DEFAULT: "#1e1b4b",
          foreground: "#f1f5f9",
        },
      },
      borderRadius: {
        lg: "0.625rem",
        md: "calc(0.625rem - 2px)",
        sm: "calc(0.625rem - 4px)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.5s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 3: Criar `frontend/src/styles/globals.css`**

```css
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap");

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    color-scheme: dark;
  }
  html {
    -webkit-tap-highlight-color: transparent;
  }
  body {
    @apply bg-bg-base text-fg-primary font-sans;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
  }
}

@layer components {
  .gradient-edge {
    background: linear-gradient(90deg, #fbbf24, #f59e0b);
  }
  .gradient-home {
    background: linear-gradient(90deg, #10b981, #34d399);
  }
  .gradient-away {
    background: linear-gradient(90deg, #ef4444, #f87171);
  }
  .text-gradient-brand {
    background: linear-gradient(90deg, #fbbf24, #10b981);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .glass-card {
    @apply bg-bg-overlay border border-white/10 backdrop-blur;
  }
  .skeleton {
    background: linear-gradient(90deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 100%);
    background-size: 200% 100%;
    @apply animate-shimmer rounded;
  }
}
```

- [ ] **Step 4: Validar a build dev**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm typecheck
```

Expected: clean.

- [ ] **Step 5: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/tailwind.config.ts frontend/postcss.config.js frontend/src/styles/globals.css
```

---

## Task 3: shadcn/ui setup + primeiros primitives

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/skeleton.tsx`
- Create: `frontend/src/components/ui/dialog.tsx`
- Create: `frontend/src/components/ui/input.tsx`

- [ ] **Step 1: Criar `frontend/components.json`**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/styles/globals.css",
    "baseColor": "neutral",
    "cssVariables": false,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 2: Criar `frontend/src/lib/utils.ts`**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 3: Adicionar Radix primitives ao package.json e instalar**

Adicione ao `dependencies` em `frontend/package.json` (manualmente, depois rode `pnpm install`):

```json
"@radix-ui/react-dialog": "^1.1.2",
"@radix-ui/react-slot": "^1.1.0",
"@radix-ui/react-tabs": "^1.1.1"
```

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm install
```

- [ ] **Step 4: Criar `frontend/src/components/ui/button.tsx`**

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-brand-primary text-bg-base hover:bg-brand-primary/90",
        ghost: "hover:bg-bg-overlay",
        outline: "border border-white/10 hover:bg-bg-overlay",
        gradient: "gradient-edge text-bg-base hover:opacity-90",
        destructive: "bg-brand-danger text-fg-primary hover:bg-brand-danger/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3 text-xs",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

- [ ] **Step 5: Criar `frontend/src/components/ui/card.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-xl border border-white/10 bg-bg-elevated text-card-foreground shadow",
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-4", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-4 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export { Card, CardHeader, CardTitle, CardContent };
```

- [ ] **Step 6: Criar `frontend/src/components/ui/badge.tsx`**

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
  {
    variants: {
      variant: {
        default: "bg-bg-overlay text-fg-muted border border-white/10",
        outcomeHome: "bg-outcome-home/20 text-outcome-home border border-outcome-home/30",
        outcomeDraw: "bg-outcome-draw/20 text-outcome-draw border border-outcome-draw/30",
        outcomeAway: "bg-outcome-away/20 text-outcome-away border border-outcome-away/30",
        edge: "gradient-edge text-bg-base border border-amber-600/30",
        live: "bg-brand-danger/20 text-brand-danger border border-brand-danger/30 animate-pulse",
        success: "bg-brand-primary/20 text-brand-primary border border-brand-primary/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
```

- [ ] **Step 7: Criar `frontend/src/components/ui/skeleton.tsx`**

```tsx
import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton h-4 w-full", className)} {...props} />;
}

export { Skeleton };
```

- [ ] **Step 8: Criar `frontend/src/components/ui/dialog.tsx`**

```tsx
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-bg-base/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out",
      className,
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-white/10 bg-bg-elevated p-6 shadow-lg sm:rounded-lg",
        className,
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)} {...props} />
);
DialogHeader.displayName = "DialogHeader";

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight", className)}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-fg-muted", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
};
```

- [ ] **Step 9: Criar `frontend/src/components/ui/input.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-white/10 bg-bg-overlay px-3 py-2 text-sm placeholder:text-fg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
```

- [ ] **Step 10: Atualizar `frontend/src/App.tsx` pra usar Button como teste**

```tsx
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function App() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-3xl font-bold text-gradient-brand">analytis</h1>
      <p className="text-fg-muted">Plano 4 — frontend live</p>
      <div className="flex gap-2">
        <Button variant="default">Default</Button>
        <Button variant="gradient">Value bet</Button>
        <Button variant="outline">Ghost</Button>
      </div>
      <div className="flex gap-2">
        <Badge variant="edge">+23% edge</Badge>
        <Badge variant="live">LIVE</Badge>
        <Badge variant="outcomeHome">HOME</Badge>
      </div>
    </main>
  );
}
```

- [ ] **Step 11: Validar**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm typecheck
pnpm dev   # smoke visual em http://localhost:5173, depois Ctrl+C
```

- [ ] **Step 12: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/package.json frontend/pnpm-lock.yaml frontend/components.json frontend/src/lib/utils.ts frontend/src/components/ui/ frontend/src/App.tsx
```

---

## Task 4: Layout shell (Header + BottomNav + roteamento esqueleto)

**Files:**
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/BottomNav.tsx`
- Create: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/pages/MatchDetailPage.tsx`
- Create: `frontend/src/pages/ValueBetsPage.tsx`
- Create: `frontend/src/pages/ClvSummaryPage.tsx`
- Create: `frontend/src/pages/NotFoundPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Criar `frontend/src/components/layout/Header.tsx`**

```tsx
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
        >
          <Settings className="h-4 w-4" />
        </button>
      </nav>
    </header>
  );
}
```

- [ ] **Step 2: Criar `frontend/src/components/layout/BottomNav.tsx`**

```tsx
import { NavLink } from "react-router-dom";
import { Gem, Home, Settings, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Jogos", icon: Home },
  { to: "/bets", label: "Bets", icon: Gem },
  { to: "/clv", label: "CLV", icon: TrendingUp },
];

export function BottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 grid grid-cols-4 border-t border-white/10 bg-bg-base/90 backdrop-blur pb-[env(safe-area-inset-bottom)]">
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
        onClick={() => alert("Em breve")}
        aria-label="Configurações"
      >
        <Settings className="h-5 w-5" />
        <span>Config</span>
      </button>
    </nav>
  );
}
```

- [ ] **Step 3: Criar `frontend/src/components/layout/AppShell.tsx`**

```tsx
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
```

- [ ] **Step 4: Criar páginas placeholder**

`frontend/src/pages/HomePage.tsx`:

```tsx
export default function HomePage() {
  return <h2 className="text-2xl font-semibold">Jogos</h2>;
}
```

`frontend/src/pages/MatchDetailPage.tsx`:

```tsx
import { useParams } from "react-router-dom";

export default function MatchDetailPage() {
  const { matchId } = useParams();
  return <h2 className="text-2xl font-semibold">Match: {matchId}</h2>;
}
```

`frontend/src/pages/ValueBetsPage.tsx`:

```tsx
export default function ValueBetsPage() {
  return <h2 className="text-2xl font-semibold">Value Bets</h2>;
}
```

`frontend/src/pages/ClvSummaryPage.tsx`:

```tsx
export default function ClvSummaryPage() {
  return <h2 className="text-2xl font-semibold">CLV Summary</h2>;
}
```

`frontend/src/pages/NotFoundPage.tsx`:

```tsx
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center gap-4 py-16">
      <h2 className="text-2xl font-semibold">404</h2>
      <p className="text-fg-muted">Página não encontrada.</p>
      <Button asChild>
        <Link to="/">Voltar pra Home</Link>
      </Button>
    </div>
  );
}
```

- [ ] **Step 5: Atualizar `frontend/src/App.tsx`**

```tsx
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
```

- [ ] **Step 6: Validar typecheck e dev server**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm typecheck
pnpm dev   # navegar nas 4 rotas
```

- [ ] **Step 7: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/src/
```

---

## Task 5: Data layer — `api.ts` + tipos

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/lib/api.test.ts`

- [ ] **Step 1: Criar `frontend/src/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 2: Escrever teste primeiro — `frontend/src/lib/api.test.ts`**

```ts
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, ApiError } from "./api";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
  localStorage.clear();
});

afterAll(() => {
  globalThis.fetch = originalFetch;
});

function mockResponse(body: unknown, init: ResponseInit = { status: 200 }) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
}

describe("api.listUpcomingMatches", () => {
  it("calls /v1/matches?upcoming=true&days=N with auth header", async () => {
    localStorage.setItem("analytis_api_key", "test-key");
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ items: [] }),
    );
    await api.listUpcomingMatches(3);
    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/v1/matches?upcoming=true&days=3");
    const init = call[1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe("test-key");
  });
});

describe("api error handling", () => {
  it("throws ApiError with status on non-2xx", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ detail: "nope" }, { status: 401 }),
    );
    await expect(api.listUpcomingMatches(1)).rejects.toMatchObject({
      status: 401,
      message: "nope",
    });
    await expect(api.listUpcomingMatches(1)).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 3: Verificar falha**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm test src/lib/api.test.ts
```

Expected: erro de import (`api` ainda não existe).

- [ ] **Step 4: Implementar `frontend/src/lib/api.ts`**

```ts
const BASE = "/v1";

function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("analytis_api_key");
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const apiKey = getApiKey();
  const headers: Record<string, string> = {
    "X-API-Key": apiKey ?? "",
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

// ----- Domain types -----
export type MatchStatus = "scheduled" | "live" | "finished" | "postponed" | "cancelled";

export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  status: MatchStatus;
  home_goals: number | null;
  away_goals: number | null;
  is_home_neutral: boolean;
}

export interface MatchesList {
  items: Match[];
}

export interface Prediction {
  market: string;
  outcome: string;
  prob: number;
  ci_low: number;
  ci_high: number;
  model_version: string;
  created_at: string;
}

export interface MatchPredictions {
  match_id: string;
  home_goals: number | null;
  away_goals: number | null;
  status: MatchStatus;
  kickoff_utc: string;
  predictions: Prediction[];
}

export interface OddsQuote {
  bookmaker: string;
  market: string;
  outcome: string;
  decimal_odds: number;
  snapshot_taken_at: string;
}

export interface OddsResponse {
  match_id: string;
  quotes: OddsQuote[];
  best_per_outcome: Record<string, { decimal_odds: number; bookmaker: string }>;
}

export interface ValueBet {
  id: string;
  match_id: string;
  model_version_id: string;
  market: string;
  outcome: string;
  bookmaker: string;
  our_prob: number;
  market_prob: number;
  decimal_odds: number;
  edge: number;
  kelly_fraction: number;
  suggested_stake_units: number;
  found_at: string;
  closing_decimal_odds: number | null;
  closing_clv: number | null;
}

export interface ValueBetsList {
  items: ValueBet[];
}

export interface ClvSummary {
  model_version: string;
  n_bets: number;
  n_with_clv: number;
  mean_clv: number | null;
  median_edge: number | null;
}

export interface ClvSummaryList {
  items: ClvSummary[];
}

// ----- Endpoints -----
export const api = {
  listUpcomingMatches: (days = 7) =>
    request<MatchesList>(`/matches?upcoming=true&days=${days}`),
  getMatchPredictions: (matchId: string) =>
    request<MatchPredictions>(`/matches/${matchId}/predictions`),
  getMatchOdds: (matchId: string) => request<OddsResponse>(`/matches/${matchId}/odds`),
  getMatchValueBets: (matchId: string) =>
    request<ValueBetsList>(`/matches/${matchId}/value-bets`),
  getClvSummary: () => request<ClvSummaryList>(`/bets/clv-summary`),
};
```

- [ ] **Step 5: Rodar testes**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm test src/lib/api.test.ts
pnpm typecheck
```

Expected: ambos os testes passam, typecheck clean.

- [ ] **Step 6: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/src/lib/api.ts frontend/src/lib/api.test.ts frontend/src/test/setup.ts
```

---

## Task 6: Auth + `ApiKeyDialog`

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/auth.test.ts`
- Create: `frontend/src/components/ApiKeyDialog.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Escrever test — `frontend/src/lib/auth.test.ts`**

```ts
import { describe, expect, it, beforeEach } from "vitest";
import { clearApiKey, getApiKey, setApiKey } from "./auth";

beforeEach(() => {
  localStorage.clear();
});

describe("auth", () => {
  it("stores and reads api key", () => {
    setApiKey("abc-123");
    expect(getApiKey()).toBe("abc-123");
  });
  it("clear removes key", () => {
    setApiKey("x");
    clearApiKey();
    expect(getApiKey()).toBeNull();
  });
  it("returns null when nothing stored", () => {
    expect(getApiKey()).toBeNull();
  });
});
```

- [ ] **Step 2: Implementar `frontend/src/lib/auth.ts`**

```ts
const KEY = "analytis_api_key";

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setApiKey(key: string): void {
  if (!key.trim()) return;
  window.localStorage.setItem(KEY, key.trim());
}

export function clearApiKey(): void {
  window.localStorage.removeItem(KEY);
}
```

- [ ] **Step 3: Criar `frontend/src/components/ApiKeyDialog.tsx`**

```tsx
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
    // Recarrega pra refazer queries com nova key
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
```

- [ ] **Step 4: Adicionar dialog no `App.tsx`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import HomePage from "@/pages/HomePage";
import MatchDetailPage from "@/pages/MatchDetailPage";
import ValueBetsPage from "@/pages/ValueBetsPage";
import ClvSummaryPage from "@/pages/ClvSummaryPage";
import NotFoundPage from "@/pages/NotFoundPage";

export default function App() {
  return (
    <BrowserRouter>
      <ApiKeyDialog />
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
```

- [ ] **Step 5: Rodar testes + typecheck**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm test
pnpm typecheck
```

- [ ] **Step 6: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/src/lib/auth.ts frontend/src/lib/auth.test.ts frontend/src/components/ApiKeyDialog.tsx frontend/src/App.tsx
```

---

## Task 7: Query client + hooks

**Files:**
- Create: `frontend/src/lib/query-client.ts`
- Create: `frontend/src/hooks/useMatches.ts`
- Create: `frontend/src/hooks/useMatchPredictions.ts`
- Create: `frontend/src/hooks/useMatchOdds.ts`
- Create: `frontend/src/hooks/useMatchValueBets.ts`
- Create: `frontend/src/hooks/useClvSummary.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Criar `frontend/src/lib/query-client.ts`**

```ts
import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      retry: (failures, err) => {
        if (err instanceof ApiError && err.status === 401) return false;
        return failures < 2;
      },
    },
  },
});
```

- [ ] **Step 2: Criar `frontend/src/hooks/useMatches.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useUpcomingMatches(days = 7) {
  return useQuery({
    queryKey: ["matches", "upcoming", days],
    queryFn: () => api.listUpcomingMatches(days),
    refetchInterval: 60_000,
  });
}
```

- [ ] **Step 3: Criar `frontend/src/hooks/useMatchPredictions.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchPredictions(matchId: string | undefined) {
  return useQuery({
    queryKey: ["match-predictions", matchId],
    queryFn: () => api.getMatchPredictions(matchId!),
    enabled: !!matchId,
  });
}
```

- [ ] **Step 4: Criar `frontend/src/hooks/useMatchOdds.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchOdds(matchId: string | undefined) {
  return useQuery({
    queryKey: ["match-odds", matchId],
    queryFn: () => api.getMatchOdds(matchId!),
    enabled: !!matchId,
    refetchInterval: 60_000,
  });
}
```

- [ ] **Step 5: Criar `frontend/src/hooks/useMatchValueBets.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchValueBets(matchId: string | undefined) {
  return useQuery({
    queryKey: ["match-value-bets", matchId],
    queryFn: () => api.getMatchValueBets(matchId!),
    enabled: !!matchId,
    refetchInterval: 60_000,
  });
}
```

- [ ] **Step 6: Criar `frontend/src/hooks/useClvSummary.ts`**

```ts
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useClvSummary() {
  return useQuery({
    queryKey: ["clv-summary"],
    queryFn: () => api.getClvSummary(),
  });
}
```

- [ ] **Step 7: Envolver `App.tsx` no `QueryClientProvider`**

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { ApiKeyDialog } from "@/components/ApiKeyDialog";
import HomePage from "@/pages/HomePage";
import MatchDetailPage from "@/pages/MatchDetailPage";
import ValueBetsPage from "@/pages/ValueBetsPage";
import ClvSummaryPage from "@/pages/ClvSummaryPage";
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
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 8: Validar typecheck**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm typecheck
```

- [ ] **Step 9: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/src/lib/query-client.ts frontend/src/hooks/ frontend/src/App.tsx
```

---

## Task 8: HomePage — MatchCard + lista cronológica

**Files:**
- Create: `frontend/src/components/matches/MatchCard.tsx`
- Create: `frontend/src/components/matches/MarketBars.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Criar `frontend/src/components/matches/MarketBars.tsx`**

```tsx
import { cn } from "@/lib/utils";

interface Props {
  home: number; // 0..1
  draw: number;
  away: number;
  compact?: boolean;
}

export function MarketBars({ home, draw, away, compact = false }: Props) {
  const fmt = (v: number) => `${Math.round(v * 100)}%`;
  return (
    <div className="space-y-1">
      <div className={cn("flex gap-1", compact ? "h-1.5" : "h-2")}>
        <div className="rounded-full gradient-home" style={{ flex: home }} />
        <div className="rounded-full bg-outcome-draw/60" style={{ flex: draw }} />
        <div className="rounded-full gradient-away" style={{ flex: away }} />
      </div>
      <div
        className={cn(
          "flex justify-between text-fg-muted font-mono",
          compact ? "text-[10px]" : "text-xs",
        )}
      >
        <span>{fmt(home)}</span>
        <span>{fmt(draw)}</span>
        <span>{fmt(away)}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Criar `frontend/src/components/matches/MatchCard.tsx`**

```tsx
import { Link } from "react-router-dom";
import { Gem } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { MarketBars } from "./MarketBars";
import type { Match } from "@/lib/api";

interface Props {
  match: Match;
  probs?: { home: number; draw: number; away: number };
  valueBetsCount?: number;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusBadge(status: Match["status"]) {
  if (status === "live") return <Badge variant="live">LIVE</Badge>;
  if (status === "finished") return <Badge variant="success">FINAL</Badge>;
  if (status === "postponed" || status === "cancelled")
    return <Badge variant="default">{status.toUpperCase()}</Badge>;
  return null;
}

export function MatchCard({ match, probs, valueBetsCount = 0 }: Props) {
  const isFinished = match.status === "finished";
  return (
    <Link to={`/matches/${match.id}`} className="block group">
      <Card className={isFinished ? "opacity-70" : ""}>
        <div className="flex items-center justify-between px-4 pt-3">
          <span className="text-[11px] uppercase tracking-wide text-fg-muted">
            {formatTime(match.kickoff_utc)}
          </span>
          {statusBadge(match.status)}
        </div>
        <div className="px-4 py-3">
          <div className="text-base font-semibold">
            {match.home_team} <span className="text-fg-muted">×</span> {match.away_team}
          </div>
          {match.home_goals !== null && match.away_goals !== null && (
            <div className="mt-1 font-mono text-2xl">
              {match.home_goals} - {match.away_goals}
            </div>
          )}
        </div>
        {probs && (
          <div className="px-4 pb-3">
            <MarketBars {...probs} />
          </div>
        )}
        {valueBetsCount > 0 && (
          <div className="px-4 pb-3">
            <Badge variant="edge" className="inline-flex items-center gap-1">
              <Gem className="h-3 w-3" />
              {valueBetsCount} value bet{valueBetsCount > 1 ? "s" : ""}
            </Badge>
          </div>
        )}
      </Card>
    </Link>
  );
}
```

- [ ] **Step 3: Atualizar `frontend/src/pages/HomePage.tsx`**

```tsx
import { useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { MatchCard } from "@/components/matches/MatchCard";
import { Button } from "@/components/ui/button";

const FILTERS = [
  { label: "Hoje", days: 1 },
  { label: "Amanhã", days: 2 },
  { label: "Semana", days: 7 },
] as const;

export default function HomePage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>(FILTERS[0]);
  const { data, isLoading, isError } = useUpcomingMatches(filter.days);

  const sortedMatches = useMemo(
    () =>
      data?.items
        .slice()
        .sort(
          (a, b) =>
            new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime(),
        ) ?? [],
    [data],
  );

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Jogos</h2>
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={filter.label === f.label ? "gradient" : "ghost"}
              size="sm"
              onClick={() => setFilter(f)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </header>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-brand-danger">
          Não foi possível carregar os jogos. Verifique se o backend está online.
        </p>
      )}

      {!isLoading && sortedMatches.length === 0 && (
        <p className="text-fg-muted text-sm py-8 text-center">
          Nenhum jogo nesse intervalo. Tente ampliar pra "Semana".
        </p>
      )}

      <div className="space-y-3">
        {sortedMatches.map((m) => (
          <MatchCard key={m.id} match={m} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Validar dev**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm typecheck
```

Em paralelo, com backend rodando:

```bash
# terminal 1: backend
cd "C:\Projetos\Pessoal\analytis"
uv run analytis api serve --port 8000

# terminal 2: frontend
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm dev
# abre http://localhost:5173 — após T19 (rota /v1/matches) deve listar jogos
```

(Ainda vai falhar até a Task 19 implementar `/v1/matches?upcoming=true`. Por ora aceita o estado de erro — visual ok.)

- [ ] **Step 5: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/src/components/matches/ frontend/src/pages/HomePage.tsx
```

---

## Task 9: HomePage — integrar predictions e value bet count nos cards

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/hooks/useMatchCardSummary.ts`

- [ ] **Step 1: Criar `frontend/src/hooks/useMatchCardSummary.ts`**

```ts
import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { api, type Match } from "@/lib/api";

export interface MatchSummary {
  probs?: { home: number; draw: number; away: number };
  valueBetsCount: number;
}

export function useMatchCardSummaries(matches: Match[]) {
  const queries = useQueries({
    queries: matches.flatMap((m) => [
      {
        queryKey: ["match-predictions", m.id],
        queryFn: () => api.getMatchPredictions(m.id),
      },
      {
        queryKey: ["match-value-bets", m.id],
        queryFn: () => api.getMatchValueBets(m.id),
      },
    ]),
  });

  return useMemo(() => {
    const summaries = new Map<string, MatchSummary>();
    matches.forEach((m, idx) => {
      const predictionsRes = queries[idx * 2];
      const betsRes = queries[idx * 2 + 1];
      const oneXTwo = predictionsRes?.data?.predictions.filter(
        (p) => p.market === "1x2",
      );
      const probs = oneXTwo && oneXTwo.length >= 3
        ? {
            home: oneXTwo.find((p) => p.outcome === "home")?.prob ?? 0,
            draw: oneXTwo.find((p) => p.outcome === "draw")?.prob ?? 0,
            away: oneXTwo.find((p) => p.outcome === "away")?.prob ?? 0,
          }
        : undefined;
      summaries.set(m.id, {
        probs,
        valueBetsCount: betsRes?.data?.items.length ?? 0,
      });
    });
    return summaries;
  }, [matches, queries]);
}
```

- [ ] **Step 2: Atualizar `HomePage.tsx`** para usar `useMatchCardSummaries`

```tsx
import { useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { useMatchCardSummaries } from "@/hooks/useMatchCardSummary";
import { MatchCard } from "@/components/matches/MatchCard";
import { Button } from "@/components/ui/button";

const FILTERS = [
  { label: "Hoje", days: 1 },
  { label: "Amanhã", days: 2 },
  { label: "Semana", days: 7 },
] as const;

export default function HomePage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>(FILTERS[0]);
  const { data, isLoading, isError } = useUpcomingMatches(filter.days);

  const sortedMatches = useMemo(
    () =>
      data?.items
        .slice()
        .sort(
          (a, b) =>
            new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime(),
        ) ?? [],
    [data],
  );

  const summaries = useMatchCardSummaries(sortedMatches);

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Jogos</h2>
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={filter.label === f.label ? "gradient" : "ghost"}
              size="sm"
              onClick={() => setFilter(f)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </header>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-brand-danger">
          Não foi possível carregar os jogos.
        </p>
      )}

      {!isLoading && sortedMatches.length === 0 && (
        <p className="text-fg-muted text-sm py-8 text-center">
          Nenhum jogo nesse intervalo.
        </p>
      )}

      <div className="space-y-3">
        {sortedMatches.map((m) => {
          const s = summaries.get(m.id);
          return (
            <MatchCard
              key={m.id}
              match={m}
              probs={s?.probs}
              valueBetsCount={s?.valueBetsCount ?? 0}
            />
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Validar typecheck**

```bash
cd "C:\Projetos\Pessoal\analytis\frontend"
pnpm typecheck
```

- [ ] **Step 4: Stage**

```bash
cd "C:\Projetos\Pessoal\analytis"
git add frontend/src/hooks/useMatchCardSummary.ts frontend/src/pages/HomePage.tsx
```

---

## Task 10: Backend wiring — nova rota `GET /v1/matches?upcoming=true&days=N`

**Files:**
- Create: `src/analytis/api/routes/matches.py`
- Modify: `src/analytis/api/main.py`
- Test: `tests/integration/api/test_matches_route.py`

- [ ] **Step 1: Escrever teste — `tests/integration/api/test_matches_route.py`**

```python
"""Integration tests for /v1/matches?upcoming=true route."""

import pytest
from fastapi.testclient import TestClient

from analytis.api.main import create_app
from analytis.config import get_settings


@pytest.mark.integration
def test_upcoming_matches_requires_api_key() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/matches?upcoming=true&days=7")
    assert resp.status_code == 401


@pytest.mark.integration
def test_upcoming_matches_returns_items_shape() -> None:
    api_key = get_settings().api_key.get_secret_value()
    app = create_app()
    client = TestClient(app)
    resp = client.get(
        "/v1/matches?upcoming=true&days=7",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    if body["items"]:
        first = body["items"][0]
        assert "id" in first
        assert "home_team" in first
        assert "away_team" in first
        assert "kickoff_utc" in first
        assert "status" in first
```

- [ ] **Step 2: Verificar falha**

```bash
export PATH="/c/Users/PC Gamer/AppData/Local/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"
uv run pytest tests/integration/api/test_matches_route.py -v -m integration
```

Expected: 404 nas duas rotas (route não existe).

- [ ] **Step 3: Implementar `src/analytis/api/routes/matches.py`**

```python
"""Routes for matches listings."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.matches import MatchORM

router = APIRouter(prefix="/matches", tags=["matches"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class MatchItem(BaseModel):
    id: UUID
    home_team: str
    away_team: str
    kickoff_utc: datetime
    status: str
    home_goals: int | None
    away_goals: int | None
    is_home_neutral: bool


class MatchesList(BaseModel):
    items: list[MatchItem]


@router.get(
    "",
    response_model=MatchesList,
    dependencies=[Depends(require_api_key)],
)
async def list_matches(
    upcoming: bool = Query(False),
    days: int = Query(7, ge=1, le=30),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> MatchesList:
    async with _session(settings) as session:
        team_rows = (
            await session.execute(select(TeamORM.id, TeamORM.name))
        ).all()
        id_to_name: dict[UUID, str] = {row.id: row.name for row in team_rows}

        stmt = select(MatchORM)
        if upcoming:
            now = datetime.now(UTC)
            stmt = stmt.where(
                MatchORM.kickoff_utc >= now,
                MatchORM.kickoff_utc < now + timedelta(days=days),
                MatchORM.status.in_(("scheduled", "live")),
            )
        stmt = stmt.order_by(MatchORM.kickoff_utc.asc()).limit(200)

        rows = list((await session.scalars(stmt)).all())
        items = [
            MatchItem(
                id=m.id,
                home_team=id_to_name.get(m.home_team_id, "?"),
                away_team=id_to_name.get(m.away_team_id, "?"),
                kickoff_utc=m.kickoff_utc,
                status=m.status,
                home_goals=m.home_goals,
                away_goals=m.away_goals,
                is_home_neutral=m.is_home_neutral,
            )
            for m in rows
        ]
        return MatchesList(items=items)
```

- [ ] **Step 4: Registrar rota em `src/analytis/api/main.py`**

```python
"""FastAPI application factory."""

from fastapi import FastAPI

from analytis import __version__
from analytis.api.routes import health, matches, models, odds, predictions, value_bets


def create_app() -> FastAPI:
    app = FastAPI(
        title="analytis",
        version=__version__,
        description="Football analytics backend — pre-match probabilistic predictions.",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.include_router(health.router, prefix="/v1")
    app.include_router(matches.router, prefix="/v1")
    app.include_router(predictions.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(odds.router, prefix="/v1")
    app.include_router(value_bets.router, prefix="/v1")
    return app


app = create_app()
```

⚠️ **Atenção:** `predictions.router` também usa prefix `/matches` (de `/v1/matches/{id}/predictions`). FastAPI mantém ambos porque os paths são distintos (`/v1/matches` vs `/v1/matches/{id}/predictions`). Sem conflito.

- [ ] **Step 5: Rodar testes + quality**

```bash
uv run pytest tests/integration/api/test_matches_route.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

- [ ] **Step 6: Stage**

```bash
git add src/analytis/api/routes/matches.py src/analytis/api/main.py tests/integration/api/test_matches_route.py
```

---

## Task 11 onwards (overview detalhado)

As tasks restantes seguem o mesmo padrão (test/code/stage) e serão detalhadas com código completo quando a execução chegar nelas. Resumo do que cada uma entrega:

### Task 11: MatchDetailPage — header sticky + tabs shell

Cria `pages/MatchDetailPage.tsx` consumindo `useMatchPredictions`, `useMatchOdds`, `useMatchValueBets`. Header sticky com bandeirinhas (emoji), nomes, hora local. Componente `Tabs` shadcn com 3 abas: "Previsões", "Odds", "Value Bets". Estado inicial da tab vem de `?tab=` na query string.

### Task 12: MatchDetailPage — tab Previsões (MarketBars + ScoreHeatmap)

Implementa MarketBars grande para 1X2, OU 2.5, BTTS. Implementa `ScoreHeatmap.tsx` — grid 6×6 colorido pela probabilidade do placar exato. Reusa as predições do hook.

### Task 13: MatchDetailPage — tab Odds (OddsTable)

Implementa `OddsTable.tsx` — tabela responsiva (cards no mobile, tabela no desktop) `Bookmaker × Outcome × Decimal Odds`. Best price por outcome destacado com badge `success` e ícone `Trophy`.

### Task 14: MatchDetailPage — tab Value Bets (ValueBetCard list)

Implementa `bets/ValueBetCard.tsx` com: jogo header, market/outcome, badge gradient `+X% edge`, decimal odds, bookmaker, Kelly fraction e suggested_stake_units em monoespaçada. Lista todas em ordem de edge desc.

### Task 15: ValueBetsPage — lista agregada

Lista todas as value bets de todos os jogos próximos. Faz um `useQueries` sobre os matches upcoming pegando `value-bets` de cada um e achata em uma lista única. Ordena por edge desc.

### Task 16: ValueBetsPage — Sheet de filtros

Adiciona shadcn `sheet` component. Filtros: modelo (select), mercado (chips), edge mínimo (slider 0-50%), bookmaker (multi-select). Estado dos filtros em `useState` na página; aplicados em memória antes do render.

### Task 17: ClvSummaryPage — stat cards + tabela por modelo

Componente `clv/StatCard.tsx` (label + value + gradient subtle). Página puxa `useClvSummary()` e renderiza 3 cards (total bets, mean CLV, mean edge) + tabela com 1 linha por modelo.

### Task 18: ClvSummaryPage — CLVChart com Recharts

Componente `clv/CLVChart.tsx` — `<LineChart>` do Recharts com `<ReferenceLine y={0}>` em destaque. Os dados vêm de um endpoint backend que ainda não existe; adicionamos `GET /v1/bets/clv-timeline?model=X` a essa task (extensão pequena).

### Task 19: Backend wiring — `/v1/bets/clv-timeline` + static mount + CLI

1. Adicionar rota em `src/analytis/api/routes/value_bets.py`: `GET /v1/bets/clv-timeline?model=NAME` → série temporal de CLV agregado por dia.
2. Em `src/analytis/api/main.py`, montar `StaticFiles(directory="frontend/dist", html=True)` em `/` **depois** de todas as rotas `/v1/*`. Se o diretório não existir, montar um fallback que retorna mensagem amigável.
3. Criar `src/analytis/cli/frontend.py` com 3 comandos: `dev`, `build`, `install` — wrappers do pnpm via `subprocess`. Registrar em `src/analytis/cli/app.py`.

### Task 20: Polish + testes

Vitest para os hooks (`useMatches`, `useMatchPredictions`, `useMatchCardSummary`, etc.) com `QueryClientProvider` mockado. Smoke tests com `render` + RTL pra cada Page (verifica que header e estados loading/empty renderizam). Lighthouse mobile review e ajustes finais.

---

## Acceptance criteria (end-of-plan)

- [ ] `cd frontend && pnpm dev` sobe Vite em `:5173` com proxy `/v1 → :8000`
- [ ] `cd frontend && pnpm build` gera `frontend/dist/` ≤ 500KB gzipped (sem fontes)
- [ ] `uv run analytis frontend build` é equivalente ao acima
- [ ] `uv run analytis api serve --port 8000` sozinho serve frontend em `/` + API em `/v1/*`
- [ ] Primeiro acesso sem API key → `ApiKeyDialog` abre; após salvar, fica persistido
- [ ] HomePage lista jogos próximos (filtros Hoje/Amanhã/Semana funcionam)
- [ ] Cards mostram bandeirinhas, hora local, barras 1X2, badge de value bets
- [ ] Click em um card abre `/matches/<id>` com 3 tabs funcionais
- [ ] ValueBetsPage mostra lista agregada com filtros aplicáveis
- [ ] ClvSummaryPage mostra 3 stat cards + chart Recharts + tabela por modelo
- [ ] Bottom nav (mobile) + Header (desktop) navegam entre as 4 rotas
- [ ] 401 reabre o `ApiKeyDialog`; 5xx mostra erro amigável
- [ ] `pnpm typecheck` clean (tsc strict, `noUncheckedIndexedAccess`, etc.)
- [ ] `pnpm lint` clean
- [ ] `pnpm test` passa (≥ 1 teste por hook + smoke test por Page)
- [ ] `uv run pytest` continua passando (+ 2 testes novos da rota `/v1/matches`)
- [ ] Lighthouse mobile (manual): Performance ≥ 90, Accessibility ≥ 95

Se algum item falhar, criar tarefa específica antes de declarar o plano concluído.
