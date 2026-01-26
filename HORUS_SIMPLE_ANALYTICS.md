# Horus - Análises Simples para Apresentação

## Objetivo

Apresentar análises climáticas de forma **clara e objetiva** para pessoas leigas, focando em:
- **Infraestrutura**: Torres, linhas de transmissão, edificações
- **Seguros**: Residencial, comercial, veículos
- **Eventos extremos**: Riscos reais e quantificáveis

**SEM foco agrícola.**

## Análises Prontas para Apresentação

### 1. Período de Retorno de Ventos Fortes

#### O Que É?
"Com que frequência ventos muito fortes acontecem nesta região?"

#### Como Apresentar

**Pergunta do cliente**: "Minha torre está em São Paulo. Qual o risco de vento forte?"

**Resposta Horus**:
```
📍 Localização: São Paulo, SP (-23.55, -46.63)
📊 Análise: 10 anos de dados (2015-2025)

Período de Retorno - Ventos Fortes:
┌─────────────────┬──────────────┬────────────────┐
│ Velocidade      │ Frequência   │ Período Retorno│
├─────────────────┼──────────────┼────────────────┤
│ > 40 km/h       │ 15 vezes/ano │ 24 dias        │
│ > 60 km/h       │ 3 vezes/ano  │ 4 meses        │
│ > 80 km/h       │ 1 vez/2 anos │ 2 anos         │
│ > 100 km/h      │ 1 vez/10 anos│ 10 anos        │
└─────────────────┴──────────────┴────────────────┘

⚠️ Último evento > 80 km/h: 15/03/2024
📈 Tendência: Eventos fortes aumentaram 15% nos últimos 5 anos
```

#### Visualização
- **Gráfico de barras**: Frequência por faixa de velocidade
- **Linha do tempo**: Eventos extremos ao longo dos anos
- **Mapa de calor**: Regiões de maior risco

---

### 2. Risco de Raios para Infraestrutura

#### O Que É?
"Qual a probabilidade de um raio atingir esta área?"

#### Como Apresentar

**Pergunta do cliente**: "Tenho um data center. Preciso de para-raios?"

**Resposta Horus**:
```
📍 Localização: Campinas, SP (-22.91, -47.06)
📊 Análise: Abril-Dezembro 2025 (8 meses de dados GLM)

Densidade de Raios:
┌────────────────────────┬─────────────┐
│ Métrica                │ Valor       │
├────────────────────────┼─────────────┤
│ Descargas/km²/ano      │ 8.5         │
│ Dias com raios/ano     │ 45 dias     │
│ Mês com mais raios     │ Janeiro     │
│ Hora de maior risco    │ 15h-18h     │
└────────────────────────┴─────────────┘

Comparação Regional:
- Sua área: 8.5 descargas/km²/ano
- Média Brasil: 6.2 descargas/km²/ano
- Ranking: Top 25% das áreas de maior risco

⚠️ RECOMENDAÇÃO: Instalação de SPDA (para-raios) é ESSENCIAL
```

#### Visualização
- **Mapa de densidade**: Raios por km² na região
- **Gráfico mensal**: Sazonalidade dos raios
- **Comparação**: Sua área vs média nacional

---

### 3. Chuvas Intensas e Risco de Alagamento

#### O Que É?
"Quantas vezes esta região alaga por ano?"

#### Como Apresentar

**Pergunta do cliente**: "Vou construir um galpão. Esta área alaga?"

**Resposta Horus**:
```
📍 Localização: Rio de Janeiro, RJ (-22.91, -43.17)
📊 Análise: 10 anos de dados (2015-2025)

Eventos de Chuva Intensa:
┌──────────────────┬──────────────┬────────────────┐
│ Intensidade      │ Frequência   │ Período Retorno│
├──────────────────┼──────────────┼────────────────┤
│ > 30mm em 1 dia  │ 8 vezes/ano  │ 1.5 meses      │
│ > 50mm em 1 dia  │ 3 vezes/ano  │ 4 meses        │
│ > 100mm em 1 dia │ 1 vez/2 anos │ 2 anos         │
│ > 150mm em 1 dia │ 1 vez/5 anos │ 5 anos         │
└──────────────────┴──────────────┴────────────────┘

Eventos Extremos Históricos:
1. 08/02/2019: 186mm em 24h (maior registrado)
2. 12/01/2022: 142mm em 24h
3. 05/03/2018: 128mm em 24h

⚠️ RISCO ALTO: Chuvas > 100mm acontecem regularmente
📋 Recomendação: Sistema de drenagem dimensionado para 150mm/dia
```

#### Visualização
- **Histograma**: Distribuição de precipitação diária
- **Curva de duração**: Probabilidade vs intensidade
- **Série temporal**: Eventos extremos marcados

---

### 4. Ondas de Calor

#### O Que É?
"Quantos dias de calor extremo tem nesta região?"

#### Como Apresentar

**Pergunta do cliente**: "Meu escritório tem ar-condicionado suficiente?"

**Resposta Horus**:
```
📍 Localização: Brasília, DF (-15.78, -47.93)
📊 Análise: 10 anos de dados (2015-2025)

Dias de Calor Extremo (Tmax > 35°C):
┌──────────┬──────────────┬──────────────────┐
│ Ano      │ Dias > 35°C  │ Onda de Calor*   │
├──────────┼──────────────┼──────────────────┤
│ 2015     │ 12 dias      │ 1 evento (4 dias)│
│ 2016     │ 18 dias      │ 2 eventos        │
│ 2017     │ 9 dias       │ 0 eventos        │
│ 2018     │ 15 dias      │ 1 evento         │
│ 2019     │ 21 dias      │ 3 eventos        │
│ 2020     │ 24 dias      │ 2 eventos        │
│ 2021     │ 19 dias      │ 2 eventos        │
│ 2022     │ 27 dias      │ 3 eventos        │
│ 2023     │ 31 dias      │ 4 eventos        │
│ 2024     │ 35 dias      │ 5 eventos        │
└──────────┴──────────────┴──────────────────┘
*Onda de Calor = 3+ dias consecutivos > 35°C

📈 TENDÊNCIA: Dias de calor extremo DOBRARAM em 10 anos
⚠️ Projeção 2025: ~40 dias de calor extremo

Impacto:
- Consumo de energia +45% em dias de pico
- Pico de demanda: 14h-16h
- Meses críticos: Setembro, Outubro
```

#### Visualização
- **Gráfico de barras**: Evolução anual de dias quentes
- **Calendário de calor**: Mapa mensal de temperatura
- **Tendência**: Regressão linear mostrando aumento

---

### 5. Tempestades Severas (Índice Composto)

#### O Que É?
"Risco de tempestade com raios, chuva forte E vento?"

#### Como Apresentar

**Pergunta do cliente**: "Tenho uma empresa de eventos ao ar livre. Quando cancelar?"

**Resposta Horus**:
```
📍 Localização: Curitiba, PR (-25.42, -49.27)
📊 Análise: 2025 (até dezembro)

Tempestades Severas em 2025:
┌────────────┬─────────┬──────────┬──────────┬───────────┐
│ Data       │ Raios   │ Chuva    │ Vento    │ Severidade│
├────────────┼─────────┼──────────┼──────────┼───────────┤
│ 15/01/2025 │ 25/km²  │ 68mm     │ 72 km/h  │ ALTA      │
│ 03/03/2025 │ 18/km²  │ 45mm     │ 58 km/h  │ MÉDIA     │
│ 22/04/2025 │ 12/km²  │ 52mm     │ 48 km/h  │ MÉDIA     │
│ 08/09/2025 │ 31/km²  │ 89mm     │ 81 km/h  │ MUITO ALTA│
│ 14/11/2025 │ 22/km²  │ 71mm     │ 65 km/h  │ ALTA      │
└────────────┴─────────┴──────────┴──────────┴───────────┘

Estatísticas Históricas (2015-2025):
- Frequência: 5-7 tempestades severas por ano
- Período de retorno: 1.5-2 meses
- Meses de maior risco: Janeiro, Setembro, Novembro
- Horário típico: 14h-19h

📅 Calendário de Risco por Mês:
Janeiro:   ████████░░ (80% - Risco ALTO)
Fevereiro: ██████░░░░ (60% - Risco MÉDIO)
Março:     ████░░░░░░ (40% - Risco BAIXO)
...
Setembro:  █████████░ (90% - Risco MUITO ALTO)
Outubro:   ███████░░░ (70% - Risco ALTO)
Novembro:  ████████░░ (80% - Risco ALTO)
Dezembro:  ██████░░░░ (60% - Risco MÉDIO)

💡 INSIGHT: Evite eventos ao ar livre em Set-Nov entre 14h-19h
```

#### Visualização
- **Matriz de risco**: Mês × Hora do dia
- **Mapa de eventos**: Plotar todas as tempestades severas
- **Alertas**: Sistema de score 0-100 para cada dia

---

### 6. Friagens e Massas de Ar Frio

#### O Que É?
"Quando faz muito frio nesta região?"

#### Como Apresentar

**Pergunta do cliente**: "Preciso dimensionar o aquecimento do prédio."

**Resposta Horus**:
```
📍 Localização: Porto Alegre, RS (-30.03, -51.23)
📊 Análise: 10 anos de dados (2015-2025)

Dias Frios (Tmin < 10°C):
┌──────────┬──────────────┬──────────────────┐
│ Ano      │ Dias < 10°C  │ Dias < 5°C       │
├──────────┼──────────────┼──────────────────┤
│ 2015     │ 45 dias      │ 8 dias           │
│ 2016     │ 52 dias      │ 12 dias          │
│ 2017     │ 38 dias      │ 5 dias           │
│ 2018     │ 41 dias      │ 9 dias           │
│ 2019     │ 36 dias      │ 6 dias           │
│ 2020     │ 48 dias      │ 11 dias          │
│ 2021     │ 43 dias      │ 7 dias           │
│ 2022     │ 39 dias      │ 8 dias           │
│ 2023     │ 35 dias      │ 4 dias           │
│ 2024     │ 42 dias      │ 9 dias           │
└──────────┴──────────────┴──────────────────┘

Média: 42 dias/ano com Tmin < 10°C

Distribuição Mensal:
Maio:     ████░░░░░░ (5 dias)
Junho:    ████████░░ (12 dias)
Julho:    ██████████ (15 dias)
Agosto:   ████████░░ (10 dias)
Setembro: ██░░░░░░░░ (3 dias)

⚠️ Friagem mais intensa: 17/07/2021 → Tmin = 1.2°C
📊 Duração média de frio: 3-5 dias consecutivos
💡 Pico de consumo energético: Julho (aquecimento)
```

#### Visualização
- **Box plot**: Distribuição de temperatura por mês
- **Histograma**: Frequência de temperaturas mínimas
- **Calendário**: Dias frios marcados por ano

---

### 7. Comparação de Risco Entre Localizações

#### O Que É?
"Qual cidade é melhor para instalar minha operação?"

#### Como Apresentar

**Pergunta do cliente**: "Tenho 3 opções de cidade. Qual tem menor risco climático?"

**Resposta Horus**:
```
📊 Comparação: São Paulo vs Curitiba vs Florianópolis
📅 Período: 10 anos (2015-2025)

┌─────────────────────┬──────────┬──────────┬────────────────┐
│ Risco               │ São Paulo│ Curitiba │ Florianópolis  │
├─────────────────────┼──────────┼──────────┼────────────────┤
│ Ventos > 80 km/h    │ 2/ano    │ 4/ano    │ 6/ano          │
│ Raios/km²/ano       │ 6.2      │ 7.8      │ 5.1            │
│ Chuva > 100mm/dia   │ 1/2anos  │ 1/3anos  │ 1/ano          │
│ Temp > 35°C         │ 8 dias   │ 2 dias   │ 4 dias         │
│ Temp < 5°C          │ 0 dias   │ 8 dias   │ 1 dia          │
│ Tempestades severas │ 5/ano    │ 7/ano    │ 4/ano          │
└─────────────────────┴──────────┴──────────┴────────────────┘

Score de Risco Geral (0-100, menor é melhor):
1. 🥇 Florianópolis: 35 pontos (RISCO BAIXO)
2. 🥈 São Paulo: 52 pontos (RISCO MÉDIO)
3. 🥉 Curitiba: 68 pontos (RISCO ALTO)

Recomendação: FLORIANÓPOLIS
- Menor frequência de eventos extremos
- Clima mais estável
- Menos variação térmica
```

#### Visualização
- **Gráfico radar**: Comparação multi-dimensional
- **Ranking**: Ordenação por tipo de risco
- **Mapas lado-a-lado**: Visualização geográfica

---

## Métricas Simples e Impactantes

### 1. Percentil de Risco
"Sua localização está no **top 10%** das áreas de maior risco de raios no Brasil"

### 2. Probabilidade Anual
"Há **80% de chance** de pelo menos um vento > 80 km/h este ano"

### 3. Valor Esperado de Perdas
"Baseado em histórico, espere **2 eventos** de chuva > 100mm este ano"

### 4. Comparação com Média Nacional
"Sua região tem **50% mais raios** que a média brasileira"

### 5. Tendência em Linguagem Simples
"Eventos de calor extremo **dobraram** nos últimos 10 anos"

---

## Dashboards Propostos

### Dashboard 1: Visão Geral de Risco
```
┌─────────────────────────────────────────────────────┐
│ 📍 Localização: São Paulo, SP                       │
│ 📊 Período: 2015-2025 (10 anos)                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Riscos Principais:                                  │
│ ⚠️  Ventos fortes: 3 eventos/ano                    │
│ ⚡ Raios: 6.2 descargas/km²/ano                     │
│ 🌧️  Chuvas intensas: 8 eventos/ano                 │
│ 🌡️  Ondas de calor: 15 dias/ano                    │
│ ❄️  Frio extremo: 2 dias/ano                        │
│                                                     │
│ Score Geral de Risco: 52/100 (MÉDIO)               │
│                                                     │
│ [Gráfico de Barras]                                 │
│ [Mapa de Calor]                                     │
│ [Linha do Tempo]                                    │
└─────────────────────────────────────────────────────┘
```

### Dashboard 2: Período de Retorno
```
┌─────────────────────────────────────────────────────┐
│ 🔄 Período de Retorno - Ventos Fortes               │
├─────────────────────────────────────────────────────┤
│                                                     │
│ > 60 km/h:  [████░░░░░░] A cada 4 meses            │
│ > 80 km/h:  [██░░░░░░░░] A cada 2 anos             │
│ > 100 km/h: [█░░░░░░░░░] A cada 10 anos            │
│                                                     │
│ Último evento > 80 km/h: 15/03/2024                │
│ Próximo esperado: ~Mar/2026                         │
│                                                     │
│ [Curva de Probabilidade]                            │
└─────────────────────────────────────────────────────┘
```

### Dashboard 3: Calendário de Risco
```
┌─────────────────────────────────────────────────────┐
│ 📅 Calendário de Risco 2025                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Janeiro:   ████████░░ 80% - Tempestades            │
│ Fevereiro: ██████░░░░ 60% - Chuvas intensas        │
│ Março:     ████░░░░░░ 40% - Ventos                 │
│ Abril:     ███░░░░░░░ 30% - Baixo risco            │
│ Maio:      ████░░░░░░ 40% - Friagens               │
│ Junho:     ███████░░░ 70% - Frio intenso           │
│ Julho:     ████████░░ 80% - Frio intenso           │
│ Agosto:    ██████░░░░ 60% - Ventos                 │
│ Setembro:  █████████░ 90% - Tempestades            │
│ Outubro:   ████████░░ 80% - Tempestades + Calor    │
│ Novembro:  ████████░░ 80% - Raios + Chuva          │
│ Dezembro:  ██████░░░░ 60% - Chuvas intensas        │
│                                                     │
│ ⚠️ Meses de maior risco: Set, Out, Nov             │
└─────────────────────────────────────────────────────┘
```

---

## Apresentações em PowerPoint

### Slide 1: Capa
```
╔═══════════════════════════════════════╗
║                                       ║
║   ANÁLISE DE RISCO CLIMÁTICO          ║
║                                       ║
║   São Paulo, SP                       ║
║   2015-2025 (10 anos de dados)        ║
║                                       ║
║   Powered by Horus                    ║
╚═══════════════════════════════════════╝
```

### Slide 2: Principais Riscos
```
PRINCIPAIS RISCOS IDENTIFICADOS

⚠️ VENTOS FORTES
   • 3 eventos/ano com ventos > 80 km/h
   • Período de retorno: 4 meses

⚡ RAIOS
   • 6.2 descargas/km²/ano
   • 25% acima da média nacional

🌧️ CHUVAS INTENSAS
   • 8 eventos/ano > 50mm
   • Maior registro: 142mm em 24h
```

### Slide 3: Período de Retorno
```
PERÍODO DE RETORNO - VENTOS

[Gráfico de Barras]
100 km/h: ████░░░░░░ 10 anos
 80 km/h: ████░░░░░░ 2 anos
 60 km/h: ████████░░ 4 meses

CONCLUSÃO: Ventos > 80 km/h são RAROS
mas acontecem a cada 2 anos
```

### Slide 4: Recomendações
```
RECOMENDAÇÕES

✅ Instalação de para-raios (risco alto)
✅ Drenagem dimensionada para 100mm/dia
✅ Estruturas resistentes a vento 100 km/h
⚠️ Monitoramento em Set-Nov (tempestades)
📊 Revisão anual de dados climáticos
```

---

## APIs Simples para Desenvolvedores

### Endpoint 1: Período de Retorno
```bash
GET /api/simple/return-period
  ?lat=-23.55
  &lon=-46.63
  &variable=wind_speed
  &thresholds=60,80,100

Response:
{
  "location": {"lat": -23.55, "lon": -46.63},
  "variable": "wind_speed",
  "period": "2015-2025",
  "return_periods": [
    {"threshold": 60, "frequency_per_year": 3, "return_period_months": 4},
    {"threshold": 80, "frequency_per_year": 0.5, "return_period_years": 2},
    {"threshold": 100, "frequency_per_year": 0.1, "return_period_years": 10}
  ]
}
```

### Endpoint 2: Risk Score
```bash
GET /api/simple/risk-score
  ?lat=-23.55
  &lon=-46.63

Response:
{
  "location": {"lat": -23.55, "lon": -46.63},
  "overall_score": 52,
  "risk_level": "MEDIUM",
  "breakdown": {
    "wind": 45,
    "lightning": 62,
    "precipitation": 48,
    "temperature": 38
  },
  "recommendation": "Instalação de para-raios recomendada"
}
```

### Endpoint 3: Comparação de Locais
```bash
POST /api/simple/compare-locations
  Body: {
    "locations": [
      {"name": "SP", "lat": -23.55, "lon": -46.63},
      {"name": "CWB", "lat": -25.42, "lon": -49.27}
    ]
  }

Response:
{
  "ranking": [
    {"name": "SP", "score": 52, "rank": 1},
    {"name": "CWB", "score": 68, "rank": 2}
  ],
  "winner": "SP",
  "reason": "Menor frequência de eventos extremos"
}
```

---

## Comunicação para Leigos

### Exemplo 1: E-mail de Relatório
```
Assunto: Análise de Risco Climático - Sua Empresa

Olá,

Analisamos 10 anos de dados climáticos da sua localização e encontramos:

✅ Boas notícias:
   • Risco geral é MÉDIO (52/100)
   • Menor que 60% das empresas no Brasil

⚠️ Pontos de atenção:
   • Raios: 6.2/km²/ano (25% acima da média)
   • Recomendamos instalação de para-raios

📊 Principais riscos:
   • Ventos fortes: A cada 4 meses
   • Chuvas intensas: 8 vezes por ano
   • Tempestades severas: 5 vezes por ano

📅 Meses críticos: Setembro, Outubro, Novembro

Relatório completo em anexo.

Atenciosamente,
Equipe Horus
```

### Exemplo 2: Relatório PDF
```
┌─────────────────────────────────────────┐
│ RELATÓRIO DE RISCO CLIMÁTICO            │
│ Período: 2015-2025 (10 anos)            │
└─────────────────────────────────────────┘

1. RESUMO EXECUTIVO
   Score Geral: 52/100 (Risco MÉDIO)

2. PRINCIPAIS RISCOS
   [Gráficos e tabelas]

3. PERÍODO DE RETORNO
   [Análises de frequência]

4. COMPARAÇÃO REGIONAL
   [Sua área vs média]

5. RECOMENDAÇÕES
   [Ações práticas]

6. ANEXOS
   [Dados técnicos]
```

---

## Conclusão

As análises simples da Horus focam em:

✅ **Linguagem clara**: Evitar jargões técnicos
✅ **Visualizações impactantes**: Gráficos simples e diretos
✅ **Métricas práticas**: Período de retorno, percentuais, rankings
✅ **Recomendações acionáveis**: O que fazer com a informação
✅ **Comparações**: Sua área vs média, entre locais

**Público-alvo**: Gerentes, diretores, tomadores de decisão sem formação técnica em climatologia

**Foco**: Infraestrutura, seguros, gestão de risco corporativo (SEM agro)
