# Horus - Capacidades Analíticas e Índices Climáticos

## O Que a Horus Faz Atualmente

### Dados Disponíveis
1. **Precipitação** (CHIRPS + MERGE)
   - Resolução: 0.05° (~5km)
   - Período: 2015-presente (10+ anos)
   - Frequência: Diária

2. **Temperatura** (ERA5-Land)
   - Máxima, Mínima, Média diárias
   - Resolução: 0.1° (~10km)
   - Período: 2015-presente
   - Frequência: Diária

3. **Vento** (ERA5-Land)
   - Velocidade do vento
   - Resolução: 0.1° (~10km)
   - Período: 2015-presente
   - Frequência: Diária

4. **Raios** (GLM - GOES-16)
   - Densidade de descargas atmosféricas
   - Resolução: 0.1° (~10km)
   - Período: Abril 2025-presente
   - Frequência: Agregação de 30 minutos

### Funcionalidade Atual
- **Análise histórica**: Séries temporais de até 10 anos
- **Cálculo de exposição**: Baseado em limiares definidos pelo usuário
- **Consultas**: Ponto, área, polígono
- **Visualização**: WMS para mapas

## O Que É Possível Analisar

### 1. Análises de Risco Climático

#### Risco Agrícola
- **Déficit hídrico**: Períodos sem chuva durante fases críticas
- **Excesso de chuva**: Encharcamento do solo
- **Estresse térmico**: Temperaturas extremas em culturas sensíveis
- **Geadas**: Temperatura mínima < 0°C ou < 5°C
- **Ventos fortes**: Danos físicos a culturas
- **Granizo (proxy)**: Raios + precipitação intensa

#### Risco de Infraestrutura
- **Ventos destrutivos**: > 60 km/h (danos a estruturas)
- **Raios**: Risco de danos elétricos
- **Chuvas intensas**: Alagamentos, deslizamentos
- **Ondas de calor**: Sobrecarga de redes elétricas

#### Risco para Seguros
- **Frequência de eventos extremos**: Sinistralidade histórica
- **Severidade de eventos**: Magnitude dos danos
- **Correlação espacial**: Eventos afetando múltiplas apólices
- **Tendências temporais**: Mudança de padrões ao longo dos anos

### 2. Análises de Padrões Climáticos

#### Sazonalidade
- **Estação chuvosa vs seca**: Identificação de períodos
- **Variação térmica sazonal**: Amplitude anual
- **Padrões de vento**: Direção e intensidade sazonais
- **Atividade elétrica**: Picos de tempestades

#### Variabilidade Interanual
- **Anos El Niño vs La Niña**: Impacto nas variáveis
- **Tendências de longo prazo**: Mudanças climáticas
- **Ciclos multi-anuais**: PDO, AMO, etc.

#### Eventos Extremos
- **Secas prolongadas**: Dias consecutivos sem chuva
- **Enchentes**: Precipitação acumulada extrema
- **Ondas de calor**: Dias consecutivos com temp > limiar
- **Friagens**: Massas de ar frio
- **Tempestades severas**: Raios + chuva + vento

### 3. Análises de Exposição

#### Exposição Atual
- **Limiares excedidos**: Contagem de eventos
- **Magnitude da exposição**: Quanto acima/abaixo do limiar
- **Duração da exposição**: Tempo em condição de risco

#### Exposição Histórica
- **Probabilidade de excedência**: Baseado em 10 anos de dados
- **Período de retorno**: Tempo médio entre eventos
- **Exposição acumulada**: Soma de eventos ao longo do tempo

## Índices Que Podem Ser Desenvolvidos

### 1. Índices Agrícolas

#### Índice de Estresse Hídrico (Water Stress Index)
```
WSI = Precipitação / Evapotranspiração Potencial

Onde ETP pode ser estimada por:
- Thornthwaite (temperatura)
- Hargreaves (temperatura + radiação solar estimada)
- Penman-Monteith simplificado
```

**Aplicação**: Identificar déficit hídrico em culturas

#### Índice de Satisfação de Necessidade Hídrica (Water Requirement Satisfaction Index)
```
WRSI = (Precipitação Acumulada / Necessidade da Cultura) × 100

Fases críticas:
- Germinação: Primeiros 15 dias
- Floração: Dias específicos por cultura
- Enchimento de grãos: Últimos 30 dias
```

**Aplicação**: Avaliar adequação da chuva para cada cultura

#### Graus-Dia de Crescimento (Growing Degree Days)
```
GDD = Σ [(Tmax + Tmin)/2 - Tbase]

Onde:
- Tbase = Temperatura base da cultura (ex: 10°C para milho)
- Valores negativos = 0
```

**Aplicação**: Prever estágios fenológicos, tempo de colheita

#### Índice de Risco de Geada (Frost Risk Index)
```
FRI = Número de dias com Tmin < Tlimiar

Limiares:
- Geada leve: Tmin < 5°C
- Geada moderada: Tmin < 2°C
- Geada severa: Tmin < 0°C
```

**Aplicação**: Avaliar risco para culturas sensíveis (café, citrus)

#### Índice de Estresse Térmico (Heat Stress Index)
```
HSI = Número de dias com Tmax > Tlimiar

Limiares por cultura:
- Trigo: Tmax > 30°C durante floração
- Milho: Tmax > 35°C
- Soja: Tmax > 32°C durante enchimento de grãos
```

**Aplicação**: Identificar danos por calor excessivo

### 2. Índices Hidrológicos

#### SPI - Standardized Precipitation Index
```
SPI = (Precipitação - Média) / Desvio Padrão

Escalas temporais:
- SPI-1: 1 mês (condições atuais)
- SPI-3: 3 meses (agricultura)
- SPI-6: 6 meses (recursos hídricos)
- SPI-12: 12 meses (reservatórios)

Classificação:
- SPI > 2.0: Extremamente úmido
- SPI 1.5 a 2.0: Muito úmido
- SPI 1.0 a 1.5: Moderadamente úmido
- SPI -1.0 a 1.0: Normal
- SPI -1.5 a -1.0: Moderadamente seco
- SPI -2.0 a -1.5: Muito seco
- SPI < -2.0: Extremamente seco
```

**Aplicação**: Monitoramento de secas e enchentes

#### Dias Consecutivos Secos (CDD - Consecutive Dry Days)
```
CDD = Máximo número de dias consecutivos com precipitação < 1mm
```

**Aplicação**: Identificar períodos de seca

#### Dias Consecutivos Úmidos (CWD - Consecutive Wet Days)
```
CWD = Máximo número de dias consecutivos com precipitação ≥ 1mm
```

**Aplicação**: Risco de enchentes, doenças fúngicas

#### Precipitação Máxima em N Dias (RxNday)
```
Rx1day = Precipitação máxima em 1 dia
Rx5day = Precipitação máxima em 5 dias consecutivos
```

**Aplicação**: Risco de alagamentos, deslizamentos

#### SPEI - Standardized Precipitation Evapotranspiration Index
```
SPEI = SPI aplicado a (Precipitação - ETP)
```

**Aplicação**: Seca considerando temperatura (mais preciso que SPI)

### 3. Índices de Severidade de Tempestades

#### Índice de Tempestade Severa (Severe Storm Index)
```
SSI = (Raios × Precipitação × Vento) / (Limiar1 × Limiar2 × Limiar3)

Onde:
- Raios > 10 descargas/km²/30min
- Precipitação > 20mm/hora
- Vento > 50 km/h
```

**Aplicação**: Identificar tempestades destrutivas

#### Índice de Risco de Granizo (Hail Risk Index)
```
HRI = f(Raios, Temp, Precipitação_intensa)

Condições:
- Raios intensos (> 20 descargas/km²)
- Temperatura ambiente adequada
- Precipitação muito intensa (> 30mm/h)
```

**Aplicação**: Proxy para granizo (sem dados diretos)

### 4. Índices de Conforto e Saúde

#### Índice de Calor (Heat Index)
```
HI = c1 + c2×T + c3×RH + c4×T×RH + c5×T² + c6×RH² + ...

Onde:
- T = Temperatura
- RH = Umidade Relativa (estimada se não disponível)
```

**Aplicação**: Estresse térmico em humanos e animais

#### Noites Tropicais (Tropical Nights)
```
TN = Número de dias com Tmin > 20°C
```

**Aplicação**: Conforto térmico, consumo de energia

#### Ondas de Calor (Heat Waves)
```
HW = Dias consecutivos com Tmax > percentil 90

Critérios:
- ≥ 3 dias consecutivos
- Tmax > percentil 90 da série histórica
```

**Aplicação**: Risco à saúde, consumo de energia

### 5. Índices Compostos para Seguros

#### Índice de Risco Agrícola Multivariado (MARI)
```
MARI = w1×(Déficit_hídrico) +
       w2×(Estresse_térmico) +
       w3×(Risco_geada) +
       w4×(Vento_forte) +
       w5×(Granizo_proxy)

Onde w1...w5 são pesos calibrados por cultura
```

**Aplicação**: Score único de risco para seguro agrícola

#### Índice de Sinistralidade Climática (CSI)
```
CSI = Σ(Eventos_extremos × Severidade × Exposição)

Para cada evento extremo identificado:
- Frequência nos últimos N anos
- Magnitude (desvio da normal)
- Área afetada
```

**Aplicação**: Precificação de prêmios de seguro

#### Índice de Correlação de Risco (RCI)
```
RCI = Correlação espacial de eventos extremos

Mede:
- Quantas apólices afetadas simultaneamente
- Raio de correlação espacial
- Probabilidade de eventos correlacionados
```

**Aplicação**: Gestão de portfólio, resseguro

### 6. Índices de Tendência Climática

#### Taxa de Mudança de Temperatura (Temperature Trend)
```
TT = (Tmédia_último_5anos - Tmédia_primeiro_5anos) / 10 anos

Em °C por década
```

**Aplicação**: Mudanças climáticas regionais

#### Taxa de Mudança de Precipitação (Precipitation Trend)
```
PT = (Precip_última_5anos - Precip_primeira_5anos) / 10 anos

Em mm/ano por década
```

**Aplicação**: Mudanças nos padrões de chuva

#### Índice de Extremos Crescentes (Increasing Extremes Index)
```
IEI = (Freq_extremos_últimos_3anos / Freq_extremos_primeiros_3anos) - 1

Em percentual
```

**Aplicação**: Avaliar se eventos extremos estão aumentando

## Aplicações por Setor

### Agricultura
1. **Seguro Paramétrico**
   - Trigger baseado em SPI, WRSI, GDD
   - Pagamentos automáticos quando índice < limiar
   - Exemplo: SPI-3 < -1.5 por 2 meses consecutivos

2. **Zoneamento de Risco**
   - Mapas de aptidão climática por cultura
   - Baseado em temperatura, chuva, GDD
   - Identificação de regiões de maior/menor risco

3. **Previsão de Safra**
   - Correlação entre índices climáticos e produtividade
   - Modelos de regressão GDD × Yield
   - Alertas precoces de quebra de safra

### Seguros
1. **Precificação Baseada em Risco**
   - Histórico de 10 anos de eventos extremos
   - Probabilidade de sinistros por região
   - Ajuste de prêmios por exposição

2. **Modelagem de Perdas**
   - Curvas de dano por tipo de evento
   - Loss ratio esperado
   - Capital de risco necessário

3. **Trigger Indexes**
   - Índices compostos para pagamento automático
   - Múltiplos gatilhos (temperatura + chuva + vento)
   - Redução de moral hazard

### Infraestrutura
1. **Manutenção Preditiva**
   - Ventos fortes → inspeção de torres
   - Raios → verificação de para-raios
   - Chuvas intensas → limpeza de drenagem

2. **Planejamento de Capacidade**
   - Ondas de calor → demanda energética
   - Padrões históricos de consumo
   - Dimensionamento de sistemas

### Recursos Hídricos
1. **Gestão de Reservatórios**
   - SPI-6 e SPI-12 para planejamento
   - Previsão de vazões
   - Alocação de água

2. **Risco de Escassez**
   - Dias consecutivos secos
   - Déficit hídrico acumulado
   - Alertas de racionamento

## Implementação Técnica

### Arquitetura de Cálculo de Índices

```python
# Exemplo: Estrutura para cálculo de índices

class ClimateIndex:
    def __init__(self, name, data_sources, temporal_window):
        self.name = name
        self.data_sources = data_sources
        self.temporal_window = temporal_window

    def calculate(self, lat, lon, start_date, end_date):
        # 1. Obter dados históricos via API Horus
        # 2. Aplicar fórmula do índice
        # 3. Retornar série temporal + estatísticas
        pass

# Índices disponíveis
indexes = {
    'SPI': SPIIndex(temporal_window='3M'),
    'GDD': GrowingDegreeDaysIndex(base_temp=10),
    'WRSI': WaterRequirementIndex(crop='corn'),
    'HSI': HeatStressIndex(threshold=32),
    'FRI': FrostRiskIndex(threshold=5),
    'MARI': MultivariteAgricultureIndex(weights=[...])
}
```

### Endpoints de API Propostos

```
GET /api/indexes/spi
  ?lat=-15.5
  &lon=-47.5
  &start_date=2015-01-01
  &end_date=2025-12-31
  &temporal_scale=3  # SPI-3

GET /api/indexes/gdd
  ?polygon=geojson
  &start_date=2024-09-01
  &end_date=2024-12-31
  &base_temp=10
  &crop=corn

GET /api/indexes/mari
  ?locations=csv_file
  &year=2024
  &crop=soybean
  &weights=custom_weights.json
```

### Visualizações

1. **Dashboards Temporais**
   - Gráfico de linha: SPI ao longo do tempo
   - Heatmap: Matriz ano × mês de índices
   - Histograma: Distribuição de valores

2. **Mapas Espaciais**
   - Mapa de calor: Índice por pixel
   - Isolinhas: Contornos de mesmo valor
   - Cluster: Regiões homogêneas

3. **Análises Comparativas**
   - Box plots: Distribuição por ano/mês
   - Scatter: Correlação entre índices
   - Tendência: Regressão temporal

## Próximos Passos

### Curto Prazo (1-3 meses)
1. ✅ Dados históricos completos (2015-2025)
2. ✅ Interpolação removida (dados nativos)
3. ⏳ Implementar índices básicos (SPI, GDD, CDD)
4. ⏳ API de cálculo de índices

### Médio Prazo (3-6 meses)
1. Adicionar umidade relativa (para HI, SPEI)
2. Adicionar radiação solar (para ETP precisa)
3. Implementar índices avançados (WRSI, MARI)
4. Dashboard de visualização

### Longo Prazo (6-12 meses)
1. Machine Learning para previsão
2. Modelos de safra crop-specific
3. Integração com dados de sinistros
4. Precificação automática de seguros

## Conclusão

A Horus possui uma base de dados robusta que permite:

✅ **Análises de Risco**: Identificar, quantificar e mapear riscos climáticos
✅ **Índices Climáticos**: Desenvolver 15+ índices reconhecidos internacionalmente
✅ **Aplicações Práticas**: Seguros, agricultura, infraestrutura, recursos hídricos
✅ **Valor Agregado**: Transformar dados em insights acionáveis

Com 10+ anos de dados históricos em resolução diária, a Horus está pronta para se tornar uma plataforma líder em análise de risco climático no Brasil.
