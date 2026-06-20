import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <pre className="my-3 overflow-x-auto rounded-md bg-bg-overlay/50 px-3 py-2 text-sm font-mono text-fg-primary border border-white/5">
      {children}
    </pre>
  );
}

function Inline({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-bg-overlay/60 px-1.5 py-0.5 text-[0.85em] font-mono">
      {children}
    </code>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        {subtitle && <p className="text-sm text-fg-muted">{subtitle}</p>}
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-relaxed text-fg-primary px-4 pb-4">
        {children}
      </CardContent>
    </Card>
  );
}

export default function MethodologyPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">Metodologia</h2>
        <p className="text-sm text-fg-muted">
          Como o analytis estima probabilidades, identifica value bets e mede o desempenho
          honestamente. Versão técnica com fórmulas — para o "porquê" prático leia os{" "}
          <a href="#disclaimers" className="text-fg-primary underline">avisos finais</a>.
        </p>
      </header>

      {/* ============================================================
          Dixon-Coles
      ============================================================ */}
      <Section
        title="1. Predições — Dixon-Coles"
        subtitle="Modelo bivariado de Poisson com correção de placar baixo."
      >
        <p>
          Cada partida é modelada como duas distribuições de Poisson independentes para os gols
          do mandante e do visitante, com taxas <Inline>λ</Inline> derivadas de parâmetros de
          ataque e defesa por seleção:
        </p>
        <Formula>{`λ_home = exp(atq_home − def_away + ha)
λ_away = exp(atq_away − def_home)`}</Formula>
        <p>
          Onde <Inline>atq_i</Inline> e <Inline>def_i</Inline> são os parâmetros de ataque/defesa
          do time <Inline>i</Inline> e <Inline>ha</Inline> é a vantagem de mando (zero em campo
          neutro). Os parâmetros são estimados via L-BFGS minimizando a log-verossimilhança
          negativa de todos os jogos históricos, opcionalmente com peso exponencial
          temporal <Inline>w(t) = exp(−δ · Δdias)</Inline>.
        </p>
        <p>
          A probabilidade conjunta de um placar exato <Inline>(i, j)</Inline> recebe a
          correção de Dixon-Coles <Inline>τ(i, j, λ_h, λ_a, ρ)</Inline> que corrige
          a hipótese de independência — placares 0–0, 1–0, 0–1 e 1–1 ocorrem mais (ou menos)
          frequentemente do que duas Poissons independentes prevêm. O parâmetro{" "}
          <Inline>ρ</Inline> é estimado junto com os ataques/defesas.
        </p>
        <Formula>{`P(i, j) = P_Poisson(i; λ_h) · P_Poisson(j; λ_a) · τ(i, j, λ_h, λ_a, ρ)`}</Formula>
        <p>Os mercados surgem como somas sobre a matriz de placares:</p>
        <Formula>{`P(home wins)  = Σ P(i, j)  para i > j
P(draw)       = Σ P(i, j)  para i = j
P(away wins)  = Σ P(i, j)  para i < j
P(over 2.5)   = Σ P(i, j)  para i + j ≥ 3
P(BTTS yes)   = Σ P(i, j)  para i ≥ 1 ∧ j ≥ 1`}</Formula>
        <p className="text-fg-muted">
          Truncamos a matriz em <Inline>max_goals = 10</Inline>; massa acima disso é
          numericamente irrelevante para futebol.
        </p>
      </Section>

      {/* ============================================================
          XGBoost
      ============================================================ */}
      <Section
        title="2. Predições — XGBoost"
        subtitle="Classificador 1X2 sobre 18 features tabulares."
      >
        <p>
          Onde Dixon-Coles captura a estrutura "força de ataque vs força de defesa", o XGBoost
          captura <strong>interações não-lineares</strong>: ELO da seleção, forma recente
          ponderada, vantagem de mando contextual, intervalo desde o último jogo,
          confederação, fase do torneio, etc. Treinado como classificador multi-classe com
          objetivo <Inline>multi:softprob</Inline>, otimizando log-loss em descida
          gradiente sobre árvores rasas (default: 400 árvores, profundidade 5,{" "}
          <Inline>lr = 0.05</Inline>).
        </p>
        <Formula>{`P(outcome = k | x) = softmax(Σ_t f_t(x))_k`}</Formula>
        <p>
          Cada <Inline>f_t</Inline> é uma árvore de regressão ajustada ao gradiente residual
          da iteração anterior — a soma converge a uma estimativa empírica das probabilidades
          1X2 condicionais às features. Diferentemente de Dixon-Coles, XGBoost não tem hipótese
          paramétrica sobre o processo gerador, mas exige <strong>muito mais
          dados</strong> para não overfittar.
        </p>
      </Section>

      {/* ============================================================
          Ensemble
      ============================================================ */}
      <Section
        title="3. Ensemble — combinando os modelos"
        subtitle="Média ponderada calibrada por pesos."
      >
        <p>
          Modelos com vieses diferentes (paramétrico × baseado em features) tendem a errar em
          situações distintas. Combinar reduz a variância sem sacrificar muito viés:
        </p>
        <Formula>{`P_ensemble(k) = w_dc · P_dc(k) + w_xgb · P_xgb(k)
                ─────────────────────────────────────
                              w_dc + w_xgb`}</Formula>
        <p>
          Pesos default são <Inline>0.5/0.5</Inline>, ajustáveis via CLI ao gerar a
          predição. Pesos ótimos podem ser estimados por grid search sobre o backtest, mas
          requerem que ambos os modelos estejam <strong>calibrados</strong> isoladamente —
          ver §7.
        </p>
      </Section>

      {/* ============================================================
          Odds + devigging
      ============================================================ */}
      <Section
        title="4. Odds e devigging"
        subtitle="Extraindo a probabilidade implícita 'limpa' do mercado."
      >
        <p>
          Casas de apostas oferecem odds <Inline>o_1, o_2, ..., o_n</Inline> sobre os{" "}
          <Inline>n</Inline> resultados de um mercado. Se fossem probabilidades honestas, suas
          implícitas <Inline>1/o_i</Inline> somariam exatamente 1. Na prática somam mais — a
          diferença é a <strong>margem da casa</strong> (vig, overround):
        </p>
        <Formula>{`M = Σ (1 / o_i)     →   normalmente entre 1.02 e 1.08`}</Formula>
        <p>
          Para comparar com o modelo, dividimos cada implícita pelo overround, distribuindo a
          margem proporcionalmente:
        </p>
        <Formula>{`p_market(i) = (1 / o_i) / M`}</Formula>
        <p>
          O método <em>proportional devig</em> assume que a margem é distribuída uniformemente
          entre os resultados. Existem variantes (Shin, power) que atribuem peso maior ao
          favorito; o analytis usa proportional por simplicidade e por ser razoável em mercados
          1X2 europeus.
        </p>
      </Section>

      {/* ============================================================
          Value Bets, EV, Kelly
      ============================================================ */}
      <Section
        title="5. Value Bets — EV e edge"
        subtitle="Quando o mercado paga mais do que o modelo prevê."
      >
        <p>
          Uma aposta é <strong>+EV</strong> (positive expected value) quando o retorno esperado
          é maior que zero. Para odd decimal <Inline>o</Inline> e probabilidade do modelo{" "}
          <Inline>p</Inline>:
        </p>
        <Formula>{`EV = p · (o − 1) − (1 − p)
   = p · o − 1`}</Formula>
        <p>
          O <strong>edge</strong> compara modelo e mercado em probabilidade:
        </p>
        <Formula>{`edge = p_model − p_market_devig`}</Formula>
        <p>
          O analytis discovery filtra apostas com <Inline>edge ≥ 0.03</Inline> (3 pp) por
          default, descartando ruído de calibração. Edge positivo <strong>não</strong> garante
          lucro de uma aposta isolada — apenas que, repetida muitas vezes sob a
          distribuição assumida pelo modelo, o retorno médio é positivo.
        </p>
      </Section>

      {/* ============================================================
          Kelly
      ============================================================ */}
      <Section
        title="6. Kelly fractional — quanto apostar"
        subtitle="Otimização de crescimento logarítmico da bankroll."
      >
        <p>
          Dado uma aposta com odd <Inline>o</Inline>, probabilidade verdadeira <Inline>p</Inline>{" "}
          e bankroll <Inline>B</Inline>, a fração ótima de Kelly é:
        </p>
        <Formula>{`f* = (p · b − q) / b      onde b = o − 1, q = 1 − p`}</Formula>
        <p>
          Full Kelly maximiza o log-crescimento esperado da bankroll a longo prazo, mas é{" "}
          <strong>brutal em drawdown</strong>: assume que <Inline>p</Inline> é exato. Como{" "}
          <Inline>p_model</Inline> tem erro estatístico, na prática usa-se{" "}
          <strong>Kelly fractional</strong>:
        </p>
        <Formula>{`stake = f* · B · fraction      (analytis default: fraction = 0.25)`}</Formula>
        <p>
          Quarter Kelly reduz variância e drawdown ao custo de menos crescimento esperado — o
          tradeoff certo enquanto não houver evidência empírica de calibração via CLV.
          O analytis também impõe um cap <Inline>max_units</Inline> (padrão 50) para limitar
          exposição absoluta por aposta.
        </p>
      </Section>

      {/* ============================================================
          CLV
      ============================================================ */}
      <Section
        title="7. CLV — Closing Line Value"
        subtitle="A única métrica honesta de skill de longo prazo."
      >
        <p>
          A <em>closing line</em> é a odd no momento da partida começar — o mercado convergiu
          para sua melhor estimativa. Bater consistentemente a linha de fechamento significa
          que você está identificando valor <strong>antes</strong> do mercado precificar
          completamente.
        </p>
        <Formula>{`CLV (log) = ln(o_bet / o_close)`}</Formula>
        <p>
          Para uma aposta de odd <Inline>o_bet = 2.10</Inline> que fechou em <Inline>o_close = 2.00</Inline>:{" "}
          <Inline>CLV = ln(2.10/2.00) ≈ +4.9%</Inline>. CLV agregado positivo sobre{" "}
          <strong>≥ 200 apostas</strong> é o sinal estatístico de que o modelo bate o mercado;
          ROI isolado em poucas apostas é ruído.
        </p>
        <p className="text-fg-muted">
          O analytis registra a odd no momento da aposta e atualiza CLV via{" "}
          <Inline>analytis bets track-clv</Inline> quando odds novas chegam (idealmente
          próximas ao kickoff).
        </p>
      </Section>

      {/* ============================================================
          Backtest + calibração
      ============================================================ */}
      <Section
        title="8. Backtest walk-forward e calibração"
        subtitle="Como validamos o pipeline antes de apostar dinheiro."
      >
        <p>
          O backtest <em>walk-forward</em> divide a história em janelas crescentes: treina em{" "}
          <Inline>[t₀, t_k]</Inline>, prevê <Inline>[t_k, t_k + Δ]</Inline>, move a janela e
          repete. Métricas agregadas (Brier score, log-loss, ECE) capturam performance
          out-of-sample <strong>sem leakage temporal</strong>.
        </p>
        <Formula>{`Brier(market) = (1/N) · Σ (p_pred(k) − 1[outcome=k])²
log-loss      = −(1/N) · Σ log(p_pred(outcome))
ECE           = Σ |freq_obs(bin) − conf_média(bin)| · n_bin / N`}</Formula>
        <p>
          ECE (Expected Calibration Error) mede <strong>calibração</strong>: se o modelo diz
          "70% chance" deveria acertar ~70% das vezes nesse bucket. O modelo Dixon-Coles
          inicial é <strong>overconfident</strong> — produz edges de 50–90% em mercados nichados
          que são quase certamente erro de calibração, não mispricing de mercado.
        </p>
        <p>
          A solução é <strong>calibração isotônica</strong> (não-paramétrica, monótona): treina
          uma função que mapeia probabilidades do modelo para frequências empíricas, fittada no
          backtest. Está implementada em <Inline>modeling/isotonic.py</Inline> mas ainda não
          wirada no pipeline de produção — próxima melhoria pendente.
        </p>
      </Section>

      {/* ============================================================
          Disclaimers
      ============================================================ */}
      <Section
        title="9. Avisos honestos"
        subtitle="Leia antes de transformar EV em decisão de aposta."
      >
        <div id="disclaimers" className="scroll-mt-20" />
        <ul className="space-y-3 list-disc pl-5">
          <li>
            <strong>Os modelos atuais são provavelmente overconfident.</strong> Edges de 50–90%
            em mercados de baixa liquidez são quase certamente erro do modelo, não valor real.
            Aplique calibração isotônica antes de tratar esses números como aproveitáveis.
          </li>
          <li>
            <strong>CLV é o único juiz.</strong> ROI positivo em 30 apostas é variância; CLV
            positivo médio sobre 200+ apostas é evidência de skill. Antes disso, considere as
            recomendações apenas como hipóteses a validar.
          </li>
          <li>
            <strong>Pinnacle não está no free tier do The Odds API.</strong> O analytis compara
            com livros secundários (Smarkets, Betfair Exchange, etc.) que são menos eficientes —
            o "edge" aparente pode ser apenas a diferença de sharpness entre books.
          </li>
          <li>
            <strong>Stake conservadoramente.</strong> Use quarter Kelly (default) ou stake fixa
            tiny até acumular evidência. Não suba o <Inline>--fraction</Inline> sem dados de CLV
            confirmando.
          </li>
          <li>
            <strong>Esta é uma ferramenta, não um tipster.</strong> Ela mostra o que o modelo
            pensa. A decisão de apostar — e o risco financeiro — é sua.
          </li>
        </ul>
      </Section>
    </div>
  );
}
