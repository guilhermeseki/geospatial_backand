# Plataforma de Monitoramento Climático
## Apresentação Executiva - 5 minutos

---

## 1. O PROBLEMA (30 segundos)

**O risco climático é invisível até que seja tarde demais.**

- Sinistros climáticos custam bilhões ao setor de resseguros
- Decisões de subscrição são tomadas com dados desatualizados
- Falta visibilidade em tempo real sobre eventos em andamento
- Análise retrospectiva acontece APÓS o prejuízo

---

## 2. A SOLUÇÃO (45 segundos)

**Plataforma de monitoramento climático em tempo real para suporte à decisão.**

### O que faz:
- **Monitora** variáveis climáticas 24/7 em qualquer região do Brasil/LatAm
- **Detecta** anomalias e eventos extremos automaticamente
- **Alerta** equipes de subscrição e sinistros em tempo real
- **Fornece** dados históricos para análise de tendências e precificação

### Como funciona:
- API REST com dados atualizados diariamente
- Histórico completo desde 1981 para análise de tendências
- Visualização geográfica via mapas WMS
- Consultas por ponto, área ou polígono customizado

---

## 3. VARIÁVEIS IMPLEMENTADAS E SUA IMPORTÂNCIA (2 minutos)

### 🌧️ **PRECIPITAÇÃO** (CHIRPS + MERGE)
**Por que importa:**
- Base para análise de **secas** e **enchentes**
- Impacto direto em: **Agro, Property, Garantia & Crédito**
- Exemplos de uso:
  - Detectar estiagem prolongada → risco de quebra de safra
  - Identificar chuvas extremas → risco de inundação urbana/rural
  - Acionar gatilhos de cobertura paramétrica

### 🌡️ **TEMPERATURA** (Máxima, Mínima, Média)
**Por que importa:**
- Ondas de calor e geadas causam perdas massivas
- Impacto direto em: **Agro, Vida e AP, Property, Garantia & Crédito**
- Exemplos de uso:
  - Geada → morte de plantações (café, laranja, cana)
  - Calor extremo → estresse térmico em gado, aumento de mortalidade
  - Temperatura sustentada fora do ideal → redução de produtividade

### ⚡ **RAIOS** (GLM - GOES-16)
**Por que importa:**
- Raios causam incêndios, danos elétricos e mortes
- Impacto direto em: **Property, Agro, Responsabilidade Civil, Vida e AP**
- Exemplos de uso:
  - Alta densidade de raios → risco de incêndio florestal
  - Tempestades severas → danos a propriedades e equipamentos
  - Correlação com eventos de granizo e tornados

### 💨 **VENTO** (Velocidade e Direção)
**Por que importa:**
- Ventos fortes causam danos estruturais e operacionais
- Impacto direto em: **Property, Engenharia, Marine & Transporte, Aeronáutico**
- Exemplos de uso:
  - Vendavais → destelhamentos, queda de torres
  - Furacões e ciclones → evacuações e interrupção de negócios
  - Operações marítimas e portuárias

### 🌾 **NDVI** (Índice de Vegetação)
**Por que importa:**
- Mede a saúde da vegetação em tempo real
- Impacto direto em: **Agro, Garantia & Crédito, ESG**
- Exemplos de uso:
  - NDVI baixo → estresse hídrico, praga ou doença
  - Monitoramento de recuperação pós-sinistro
  - Validação de área plantada vs. declarada

### ☀️ **RADIAÇÃO SOLAR** (Em implementação)
**Por que importa:**
- Essencial para energia solar e produtividade agrícola
- Impacto direto em: **Engenharia, Agro, Financial Lines, ESG**
- Exemplos de uso:
  - Avaliar viabilidade de projetos solares
  - Calcular perdas por baixa insolação
  - Prever produtividade de culturas fotossensíveis

---

## 4. RELEVÂNCIA POR LINHA DE NEGÓCIO (1 minuto)

| Linha de Negócio | Variáveis Críticas | Casos de Uso |
|------------------|-------------------|--------------|
| **Agro** | Precipitação, Temperatura, NDVI, Raios | Seguro paramétrico, avaliação de sinistros, precificação dinâmica |
| **Property & Engenharia** | Precipitação, Vento, Raios, Temperatura | Análise de risco de localização, resposta a eventos extremos |
| **Garantia & Crédito** | Precipitação, Temperatura, NDVI | Monitoramento de performance de safra, early warning de inadimplência |
| **Vida e AP** | Temperatura, Raios | Eventos de mortalidade em massa (ondas de calor) |
| **Responsabilidade Civil** | Raios, Vento, Precipitação | Eventos que causam danos a terceiros |
| **Marine & Transporte** | Vento, Precipitação, Raios | Condições marítimas, rotas seguras |
| **Climático** | TODAS | Cobertura paramétrica, índices de gatilho |
| **ESG** | NDVI, Radiação Solar | Monitoramento de compromissos ambientais |

---

## 5. PRÓXIMOS PASSOS: ÍNDICES DE ANOMALIA (45 segundos)

### O que são:
**Índices que quantificam o quão anormal está uma condição climática em relação ao histórico.**

### Exemplos:
- **SPI** (Standardized Precipitation Index) → mede severidade de secas
- **Desvio de temperatura** → identifica ondas de calor/frio
- **Anomalia de NDVI** → detecta estresse de vegetação vs. média histórica
- **Frequência de raios anômala** → preditor de tempestades severas

### Por que importar:
- Transforma dados brutos em **sinais acionáveis**
- Permite **alertas automáticos** quando anomalia ultrapassa threshold
- Facilita **comunicação com clientes** (ex: "região está em seca severa - SPI -2.5")
- Base para **modelos preditivos** de sinistralidade

---

## 6. CONCLUSÃO (30 segundos)

### Valor imediato:
✅ Redução de tempo de análise de sinistros (dias → minutos)
✅ Suporte a decisões de subscrição baseadas em dados atuais
✅ Diferencial competitivo em produtos paramétricos
✅ Visibilidade proativa sobre riscos emergentes

### Investimento necessário:
- Plataforma já implementada e operacional
- Custo incremental baixo (infraestrutura cloud + APIs públicas)
- ROI positivo desde o primeiro sinistro evitado ou melhor precificado

---

## DEMONSTRAÇÃO PRÁTICA

**Cenário: Seca no Centro-Oeste (Jan-Mar 2024)**

1. Consultar precipitação acumulada dos últimos 90 dias
2. Comparar com média histórica (1981-2010)
3. Identificar municípios com déficit > 50%
4. Cruzar com NDVI para confirmar estresse de vegetação
5. Gerar lista de apólices em risco na região
6. **Ação**: Contatar segurados, ajustar reservas, preparar regulação

**Tempo de análise:**
- Sem plataforma: 2-3 dias (coleta manual, planilhas)
- Com plataforma: 15 minutos (queries automáticas)

---

## PERGUNTAS FREQUENTES

**Q: Os dados são confiáveis?**
A: Sim. Usamos fontes oficiais e científicas:
- CHIRPS (UCSB/NASA) - padrão global para precipitação
- ERA5 (ECMWF) - reanálise climática mais avançada do mundo
- GOES-16 (NOAA) - satélite meteorológico oficial das Américas
- Sentinel-2/MODIS (ESA/NASA) - padrão ouro para vegetação

**Q: Quanto custa manter isso?**
A: Custo operacional baixo (~R$ 500-1000/mês cloud). Todos os dados são públicos e gratuitos.

**Q: Posso integrar com nossos sistemas?**
A: Sim. API REST documentada (OpenAPI/Swagger), integrável com qualquer sistema moderno.

**Q: Quem mais usa esse tipo de plataforma?**
A: Resseguradoras globais (Swiss Re, Munich Re), bancos (índices climáticos para crédito rural), seguradoras paramétricas (AgroInsurance, etc).

---

## CONTATO E PRÓXIMOS PASSOS

**Demonstração técnica completa:** [Agendar 30min]
**Documentação da API:** http://localhost:8000/docs
**Repositório:** /opt/geospatial_backend

**Próximas implementações:**
1. Índices de anomalia (SPI, desvios padronizados)
2. Alertas automáticos via email/webhook
3. Dashboard executivo com KPIs de risco
4. Integração com sistema de apólices
