# Plataforma de Dados Climáticos Geoespaciais - Guia de Implantação

## Sumário Executivo

Este documento apresenta a arquitetura de infraestrutura em nuvem recomendada para implantação da Plataforma de API de Dados Climáticos Geoespaciais e sua integração com aplicações frontend. A plataforma fornece dados climáticos em tempo real e históricos (precipitação, temperatura, raios, NDVI) através de uma API REST de alto desempenho com suporte do GeoServer para visualização de mapas.

---

## Índice

1. [Visão Geral do Sistema](#visão-geral-do-sistema)
2. [Recomendações de Infraestrutura em Nuvem](#recomendações-de-infraestrutura-em-nuvem)
3. [Arquitetura de Implantação na AWS](#arquitetura-de-implantação-na-aws)
4. [Integração com Frontend](#integração-com-frontend)
5. [Estimativa de Custos](#estimativa-de-custos)
6. [Checklist de Implantação](#checklist-de-implantação)
7. [Monitoramento e Manutenção](#monitoramento-e-manutenção)

---

## 1. Visão Geral do Sistema

### Componentes da Plataforma

A plataforma consiste em quatro componentes principais:

1. **Backend FastAPI** - API RESTful servindo consultas de dados climáticos
2. **GeoServer** - Servidor de tiles de mapas para visualização WMS
3. **Pipeline de Processamento de Dados** - Fluxos Prefect para ingestão automatizada de dados
4. **Armazenamento de Dados** - Arquivos NetCDF históricos + mosaicos GeoTIFF

### Fontes de Dados Atuais

- **Precipitação**: CHIRPS, MERGE (diário, resolução 5km)
- **Temperatura**: ERA5 (min/max/média, diário, resolução 9km)
- **Raios**: GLM FED (GOES-16, resolução 8km, janelas de 30min)
- **NDVI**: Sentinel-2 (10m), MODIS (250m, composições de 16 dias)

### Volume de Dados

- **NetCDF Histórico**: ~500 MB por ano por dataset
- **Mosaicos GeoTIFF**: ~2 MB por dia por dataset
- **Armazenamento Total**: ~50-100 GB para arquivo histórico completo (2018-presente)
- **Crescimento Diário**: ~10-20 MB por dia em todos os datasets

---

## 2. Recomendações de Infraestrutura em Nuvem

### Por Que Implantação em Nuvem?

✅ **Escalabilidade**: Lidar com picos de tráfego durante eventos climáticos extremos
✅ **Confiabilidade**: Uptime de 99,9%+ com recuperação automática
✅ **Acesso Global**: Integração com CDN para usuários em todo o mundo
✅ **Eficiência de Custos**: Pague apenas pelos recursos utilizados
✅ **Recuperação de Desastres**: Backups automatizados e redundância

### Provedor de Nuvem Recomendado: **Amazon Web Services (AWS)**

**Justificativa:**
- Serviços líderes de mercado para dados geoespaciais (S3, EFS, CloudFront)
- Excelente suporte ao ecossistema Python/FastAPI
- Preços competitivos para computação e armazenamento
- Forte certificação de conformidade e segurança
- Integração nativa com ferramentas de monitoramento

**Opções Alternativas:**
- **Google Cloud Platform (GCP)**: Melhor integração com BigQuery para analytics
- **Microsoft Azure**: Melhor para ambientes corporativos Microsoft
- **DigitalOcean**: Configuração mais simples, menor custo para implantações pequenas/médias

---

## 3. Arquitetura de Implantação na AWS

### Diagrama de Arquitetura

```
                                    ┌─────────────────┐
                                    │   CloudFront    │
                                    │   (CDN + SSL)   │
                                    └────────┬────────┘
                                             │
                        ┌────────────────────┴────────────────────┐
                        │                                         │
                   ┌────▼─────┐                            ┌─────▼────┐
                   │   ALB    │                            │   ALB    │
                   │ (FastAPI)│                            │(GeoServer)│
                   └────┬─────┘                            └─────┬────┘
                        │                                         │
         ┌──────────────┴──────────────┐               ┌─────────┴─────────┐
         │                             │               │                   │
    ┌────▼────┐                  ┌────▼────┐     ┌────▼────┐        ┌────▼────┐
    │  ECS    │                  │  ECS    │     │  EC2    │        │  EC2    │
    │FastAPI 1│                  │FastAPI 2│     │GeoServer│        │GeoServer│
    │ (Task)  │                  │ (Task)  │     │ Primário│        │ Standby │
    └────┬────┘                  └────┬────┘     └────┬────┘        └────┬────┘
         │                             │               │                   │
         └──────────────┬──────────────┘               └─────────┬─────────┘
                        │                                         │
                   ┌────▼─────────────────────────────────────────▼────┐
                   │              Amazon EFS (NFS)                      │
                   │  /mnt/workwork/geoserver_data (NetCDF + GeoTIFF)  │
                   └────────────────────────────────────────────────────┘
                        │
                   ┌────▼─────┐
                   │   S3     │
                   │ (Backups)│
                   └──────────┘

         ┌─────────────────────────────────────────────────────────┐
         │  Servidor Prefect (ECS Fargate) - Processamento         │
         │  - Fluxo Temperatura ERA5 (diário, agendado)            │
         │  - Fluxo Precipitação CHIRPS (diário, agendado)         │
         │  - Fluxo Raios GLM (diário, agendado)                   │
         │  - Fluxos NDVI (semanal, agendado)                      │
         └─────────────────────────────────────────────────────────┘
```

### Especificações Detalhadas dos Componentes

#### 3.1 Application Load Balancer (ALB)
- **Propósito**: Distribuir tráfego, terminação SSL, verificações de saúde
- **Tipo**: Application Load Balancer
- **Listeners**:
  - Porta 443 (HTTPS) → Containers FastAPI
  - Porta 8080 (HTTP) → Instâncias GeoServer
- **Certificado SSL**: AWS Certificate Manager (gratuito)
- **Health Check**: Endpoint `/health` (FastAPI), `/geoserver/rest/about/version` (GeoServer)

#### 3.2 Backend FastAPI (ECS Fargate)
- **Serviço**: Elastic Container Service (ECS) com Fargate
- **Imagem do Container**: Imagem Docker customizada (FastAPI + dependências)
- **Definição de Task**:
  - CPU: 2 vCPU
  - Memória: 8 GB RAM
  - Porta do Container: 8000
- **Auto-scaling**:
  - Mínimo: 2 tasks
  - Máximo: 10 tasks
  - Scale-out: CPU > 70% ou Contagem de requisições > 1000/min
  - Scale-in: CPU < 30% por 5 minutos
- **Variáveis de Ambiente**:
  - `DATA_DIR=/mnt/efs/geoserver_data`
  - `GEOSERVER_URL=http://internal-alb-geoserver.internal:8080`
  - Credenciais de banco de dados (AWS Secrets Manager)

#### 3.3 GeoServer (Instâncias EC2)
- **Tipo de Instância**: `m5.2xlarge` (8 vCPU, 32 GB RAM)
- **Sistema Operacional**: Ubuntu 22.04 LTS
- **Armazenamento**:
  - Root: 50 GB gp3 SSD
  - Dados: Montar EFS em `/mnt/geoserver_data`
- **Configuração**:
  - Java Heap: 24 GB
  - GeoWebCache habilitado (cache de tiles)
  - Serviços WMS/WFS habilitados
- **Alta Disponibilidade**:
  - Configuração Primário-Standby
  - Verificações de saúde via ALB
  - Failover automático

#### 3.4 Armazenamento Compartilhado (Amazon EFS)
- **Tipo**: Elastic File System (NFS v4)
- **Modo de Performance**: General Purpose
- **Modo de Throughput**: Bursting (ou Provisionado para cargas pesadas)
- **Classe de Armazenamento**: Standard (acesso frequente)
- **Política de Ciclo de Vida**: Mover para Acesso Infrequente após 30 dias (opcional)
- **Backup**: AWS Backup (snapshots diários, retenção de 30 dias)
- **Caminho de Montagem**: `/mnt/geoserver_data`
- **Estrutura de Diretórios**:
  ```
  /mnt/geoserver_data/
  ├── chirps/          # Mosaicos GeoTIFF CHIRPS
  ├── chirps_hist/     # NetCDF histórico CHIRPS
  ├── merge/           # Mosaicos GeoTIFF MERGE
  ├── merge_hist/      # NetCDF histórico MERGE
  ├── temp_max/        # GeoTIFFs temp máxima ERA5
  ├── temp_max_hist/   # NetCDF temp máxima ERA5
  ├── glm_fed/         # GeoTIFFs raios GLM
  ├── glm_fed_hist/    # NetCDF raios GLM
  └── raw/             # Cache temporário de download
  ```

#### 3.5 Armazenamento de Backup (Amazon S3)
- **Bucket**: `geospatial-climate-data-backup`
- **Propósito**:
  - Arquivamento de longo prazo de arquivos NetCDF históricos
  - Recuperação de desastres
  - Rastreamento de linhagem de dados
- **Política de Ciclo de Vida**:
  - Armazenamento Standard por 90 dias
  - Glacier para dados históricos > 1 ano
- **Replicação**: Replicação entre regiões (opcional, para conformidade)
- **Versionamento**: Habilitado (manter últimas 3 versões)

#### 3.6 Processamento de Dados (Prefect no ECS Fargate)
- **Serviço**: Cluster ECS Fargate para fluxos Prefect
- **Definições de Task**:
  - **Fluxo Temperatura ERA5**: 2 vCPU, 16 GB RAM
  - **Fluxo CHIRPS/MERGE**: 2 vCPU, 8 GB RAM
  - **Fluxo Raios GLM**: 4 vCPU, 16 GB RAM (downloads paralelos)
  - **Fluxos NDVI**: 2 vCPU, 8 GB RAM
- **Agendamento**: EventBridge Rules (cron)
  - Diário: 02:00 UTC (ERA5, CHIRPS, MERGE, GLM)
  - Semanal: Domingo 03:00 UTC (NDVI)
- **Armazenamento**: Montar mesmo EFS para saída
- **Logs**: CloudWatch Logs
- **Notificações**: Tópicos SNS para sucesso/falha

#### 3.7 CDN & SSL (CloudFront)
- **Propósito**: Entrega global de conteúdo, proteção DDoS, cache
- **Comportamentos de Cache**:
  - `/wms*`: Cache por 1 hora (tiles do GeoServer)
  - `/api/*`: Sem cache (dados dinâmicos)
- **SSL**: Redirecionamento automático HTTPS
- **Domínio Personalizado**: `api.sua-empresa.com`, `maps.sua-empresa.com`
- **Restrições Geográficas**: Opcional (ex: restringir a países específicos)

#### 3.8 Monitoramento e Observabilidade
- **Métricas CloudWatch**:
  - Tempos de resposta da API
  - Taxas de requisição
  - Taxas de erro
  - Throughput EFS
  - CPU/Memória dos containers
- **Alarmes CloudWatch**:
  - Taxa de erro da API > 5%
  - Falhas de tasks ECS
  - Armazenamento EFS > 80%
- **Logs CloudWatch**:
  - Logs da aplicação FastAPI
  - Logs do GeoServer
  - Logs dos fluxos Prefect
- **Application Performance Monitoring (APM)**:
  - AWS X-Ray para rastreamento de requisições
  - Ou terceiros: DataDog, New Relic

---

## 4. Integração com Frontend

### 4.1 Opções de Arquitetura Frontend

#### Opção A: Aplicação Web React/Next.js (Recomendada)

**Stack Tecnológico:**
- **Framework**: Next.js 14+ (React com SSR/SSG)
- **Biblioteca de Mapas**: Leaflet ou MapLibre GL JS
- **Gerenciamento de Estado**: React Query (para cache de API)
- **Componentes UI**: Material-UI ou Shadcn/ui
- **Gráficos**: Recharts ou Chart.js
- **Hospedagem**: AWS Amplify ou Vercel

**Funcionalidades:**
- Mapa interativo com sobreposição de camadas WMS
- Gráficos de séries temporais para dados históricos
- Busca e favoritos de localização
- Configuração de alertas de limiar
- Exportação de dados (CSV, JSON)
- Design responsivo (mobile + desktop)

**Código de Exemplo de Integração:**

```javascript
// pages/api/precipitation/history.js
import axios from 'axios';

export default async function handler(req, res) {
  const { lat, lon, start_date, end_date, source } = req.query;

  try {
    const response = await axios.post(
      `${process.env.API_BASE_URL}/precipitation/history`,
      {
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        start_date,
        end_date,
        source: source || 'chirps'
      }
    );

    res.status(200).json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
```

```jsx
// components/PrecipitationMap.jsx
import { MapContainer, TileLayer, WMSTileLayer } from 'react-leaflet';

export default function PrecipitationMap({ date, source }) {
  const wmsUrl = `${process.env.NEXT_PUBLIC_API_URL}/precipitation/wms`;

  return (
    <MapContainer center={[-15, -55]} zoom={4} style={{ height: '600px' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <WMSTileLayer
        url={wmsUrl}
        layers={source}
        format="image/png"
        transparent={true}
        version="1.1.1"
        time={date}
      />
    </MapContainer>
  );
}
```

#### Opção B: Aplicativo Mobile (Flutter)

**Stack Tecnológico:**
- **Framework**: Flutter 3.x
- **Mapas**: flutter_map + MapLibre
- **Cliente HTTP**: dio
- **Gerenciamento de Estado**: Riverpod ou Provider
- **Plataformas**: iOS + Android

**Funcionalidades:**
- Modo offline com tiles em cache
- Notificações push para alertas climáticos
- Detecção de localização baseada em GPS
- Sincronização de dados em background

#### Opção C: Dashboard (Streamlit/Dash)

**Stack Tecnológico:**
- **Framework**: Streamlit (Python) ou Dash (Plotly)
- **Visualização**: Plotly, Folium
- **Hospedagem**: AWS App Runner ou EC2

**Caso de Uso**: Dashboard analítico interno, prova de conceito

### 4.2 Exemplos de Integração da API

#### Autenticação (se habilitada)

```javascript
// utils/api.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${process.env.API_KEY}` // Opcional
  }
});

export default apiClient;
```

#### Buscar Precipitação Histórica

```javascript
// services/precipitation.js
import apiClient from '@/utils/api';

export const buscarHistoricoPrecipitacao = async (params) => {
  const response = await apiClient.post('/precipitation/history', {
    lat: params.lat,
    lon: params.lon,
    start_date: params.dataInicio,
    end_date: params.dataFim,
    source: params.fonte || 'chirps'
  });

  return response.data;
};
```

#### Buscar Gatilhos de Temperatura

```javascript
// services/temperature.js
export const buscarGatilhosTemperatura = async (params) => {
  const response = await apiClient.post('/temperature/triggers', {
    lat: params.lat,
    lon: params.lon,
    start_date: params.dataInicio,
    end_date: params.dataFim,
    threshold: params.limiar,
    operator: params.operador, // 'gt', 'lt', 'gte', 'lte'
    variable: params.variavel, // 'temp_max', 'temp_min', 'temp'
    source: 'era5'
  });

  return response.data;
};
```

#### Exibir Camada de Mapa WMS

```javascript
// components/MapView.jsx
import React, { useState } from 'react';
import { MapContainer, TileLayer, WMSTileLayer } from 'react-leaflet';

export default function MapView() {
  const [data, setData] = useState('2025-11-30');
  const [camada, setCamada] = useState('chirps');

  return (
    <div>
      <div className="controles">
        <input
          type="date"
          value={data}
          onChange={(e) => setData(e.target.value)}
        />
        <select value={camada} onChange={(e) => setCamada(e.target.value)}>
          <option value="chirps">Precipitação CHIRPS</option>
          <option value="merge">Precipitação MERGE</option>
          <option value="temp_max">Temperatura Máxima ERA5</option>
          <option value="glm_fed">Raios GLM</option>
        </select>
      </div>

      <MapContainer center={[-15, -55]} zoom={4} style={{ height: '600px' }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <WMSTileLayer
          url={`${process.env.NEXT_PUBLIC_API_URL}/${camada}/wms`}
          layers={camada}
          format="image/png"
          transparent={true}
          time={data}
        />
      </MapContainer>
    </div>
  );
}
```

### 4.3 Recomendações de Hospedagem Frontend

#### AWS Amplify (Recomendado para React/Next.js)
- **Auto-deploy**: Integração Git (push para deploy)
- **SSL**: Certificados HTTPS gratuitos
- **CDN**: Distribuição CloudFront global
- **Variáveis de Ambiente**: Gerenciamento seguro de configuração
- **Custo**: ~R$75-250/mês (baseado no tráfego)

#### Vercel (Alternativa)
- **Otimizado para Next.js**: Melhor performance para apps Next.js
- **Funções serverless**: Rotas de API integradas
- **Cache edge**: Entrega global ultra-rápida
- **Custo**: Tier gratuito disponível, Pro R$100/mês

#### AWS S3 + CloudFront (Sites Estáticos)
- **Custo-efetivo**: ~R$5-25/mês para sites pequenos
- **Deploy simples**: `aws s3 sync build/ s3://bucket`
- **Melhor para**: Sites puramente estáticos (sem SSR)

---

## 5. Estimativa de Custos

### Detalhamento de Custos Mensais na AWS (Tráfego Médio)

| Serviço | Especificação | Custo Mensal (R$) |
|---------|--------------|-------------------|
| **ECS Fargate (FastAPI)** | 2 tasks × 2 vCPU, 8GB, 24/7 | R$ 600 |
| **EC2 (GeoServer)** | 1× m5.2xlarge, 24/7 | R$ 1.400 |
| **Armazenamento EFS** | 100 GB, General Purpose | R$ 150 |
| **Backup S3** | 500 GB Standard + 2 TB Glacier | R$ 125 |
| **Application Load Balancer** | 2× ALBs | R$ 200 |
| **CloudFront (CDN)** | 1 TB transferência de dados | R$ 425 |
| **Logs/Métricas CloudWatch** | Monitoramento padrão | R$ 100 |
| **Transferência de Dados** | 500 GB/mês | R$ 225 |
| **Fluxos Prefect (ECS)** | 4 tasks diárias, média 2 horas | R$ 150 |
| **RDS PostgreSQL** (opcional) | db.t3.medium | R$ 300 |
| **AWS Backup** | Snapshots diários EFS | R$ 50 |
| **Route 53 DNS** | 1 hosted zone | R$ 5 |
| **Total** | | **~R$ 3.750/mês** |

### Dicas de Otimização de Custos

1. **Instâncias Reservadas**: Economize 30-40% em EC2 com compromisso de 1 ano
2. **Spot Instances**: Use para processamento Prefect (economize 70%)
3. **EFS Acesso Infrequente**: Mova dados antigos para classe de armazenamento IA
4. **S3 Intelligent Tiering**: Otimização automática de custos
5. **Métricas CloudWatch**: Reduza retenção de 15 meses para 3 meses
6. **Right-sizing**: Monitore e reduza recursos superprovisionados

### Cenários de Escalonamento de Tráfego

| Cenário | Usuários/Dia | Chamadas API/Dia | Custo Mensal |
|----------|--------------|------------------|--------------|
| **Pequeno** | <1.000 | <10.000 | R$ 1.500-2.500 |
| **Médio** | 1.000-10.000 | 10.000-100.000 | R$ 3.750-7.500 |
| **Grande** | 10.000-100.000 | 100.000-1M | R$ 10.000-25.000 |
| **Empresarial** | >100.000 | >1M | R$ 25.000+ |

---

## 6. Checklist de Implantação

### Fase 1: Configuração de Infraestrutura (Semana 1)

- [ ] Criar conta AWS e configurar alertas de billing
- [ ] Configurar VPC com sub-redes públicas/privadas (multi-AZ)
- [ ] Criar sistema de arquivos EFS e mount targets
- [ ] Configurar buckets S3 para backups e estado do Terraform
- [ ] Configurar roles e políticas IAM (privilégio mínimo)
- [ ] Criar repositórios ECR para imagens Docker
- [ ] Configurar Application Load Balancers (FastAPI + GeoServer)
- [ ] Solicitar certificados SSL via AWS Certificate Manager
- [ ] Configurar DNS no Route 53 (se usar domínio personalizado)

### Fase 2: Implantação da Aplicação (Semana 2)

- [ ] Construir e enviar imagens Docker para ECR
  - [ ] Imagem da aplicação FastAPI
  - [ ] Imagem do worker Prefect
- [ ] Implantar GeoServer em instâncias EC2
  - [ ] Instalar Java 11/17
  - [ ] Configurar GeoServer com configurações JVM otimizadas
  - [ ] Montar EFS e configurar diretórios de dados
  - [ ] Configurar GeoWebCache para cache de tiles
- [ ] Implantar FastAPI via ECS Fargate
  - [ ] Criar definições de tasks
  - [ ] Configurar políticas de auto-scaling
  - [ ] Definir variáveis de ambiente (Secrets Manager)
- [ ] Implantar servidor Prefect no ECS
  - [ ] Configurar banco de dados Prefect (RDS ou externo)
  - [ ] Registrar fluxos e agendamentos
- [ ] Configurar monitoramento e alarmes CloudWatch

### Fase 3: Migração de Dados (Semana 3)

- [ ] Fazer upload de arquivos NetCDF históricos para EFS (usar DataSync ou rsync)
- [ ] Fazer upload de mosaicos GeoTIFF para EFS
- [ ] Verificar se GeoServer consegue ler stores ImageMosaic
- [ ] Testar endpoints da API com dados de exemplo
- [ ] Executar fluxos iniciais de processamento de dados
  - [ ] Temperatura ERA5 (últimos 30 dias)
  - [ ] Precipitação CHIRPS (últimos 30 dias)
  - [ ] Raios GLM (últimos 30 dias)
- [ ] Verificar se camadas WMS renderizam corretamente

### Fase 4: Integração com Frontend (Semana 4)

- [ ] Configurar repositório frontend (GitHub/GitLab)
- [ ] Configurar variáveis de ambiente (URLs da API, chaves)
- [ ] Implementar camada de integração da API
- [ ] Construir componentes de visualização de mapas
- [ ] Construir formulários de consulta de dados e gráficos
- [ ] Configurar pipeline CI/CD (GitHub Actions ou AWS CodePipeline)
- [ ] Implantar frontend no AWS Amplify ou Vercel
- [ ] Configurar domínio personalizado e SSL

### Fase 5: Testes e Go-Live (Semana 5)

- [ ] Testes de carga (Apache JMeter ou Locust)
- [ ] Auditoria de segurança (testes de penetração, OWASP)
- [ ] Revisão de documentação
- [ ] Testes de aceitação do usuário (UAT)
- [ ] Simulação de recuperação de desastres (restaurar do backup)
- [ ] Otimização de performance baseada em monitoramento
- [ ] Anúncio de go-live e treinamento
- [ ] Monitoramento pós-lançamento (primeiras 48 horas)

---

## 7. Monitoramento e Manutenção

### Indicadores-Chave de Performance (KPIs)

| Métrica | Meta | Ação se Excedido |
|---------|------|------------------|
| Tempo de Resposta API (p95) | <500ms | Escalar tasks ECS |
| Taxa de Erro da API | <1% | Verificar logs, reiniciar serviços |
| Atraso Processamento Dados | <6 horas | Aumentar workers Prefect |
| Throughput EFS | <80% capacidade | Upgrade para Throughput Provisionado |
| Renderização Tiles GeoServer | <2s | Otimizar estilos, aumentar cache |

### Tarefas Diárias de Monitoramento

- Verificar dashboard CloudWatch para anomalias
- Revisar execuções de fluxos Prefect (sucesso/falha)
- Monitorar uso de armazenamento EFS
- Verificar logs de erros da API

### Tarefas Semanais de Manutenção

- Revisar relatórios de custo e uso
- Atualizar patches de segurança (SO, dependências)
- Verificar integridade de backups
- Revisar e otimizar queries lentas

### Tarefas Mensais de Manutenção

- Revisar e atualizar políticas de auto-scaling
- Analisar padrões de tráfego e ajustar recursos
- Atualizar datasets (ex: novas composições NDVI)
- Auditoria de segurança e verificação de conformidade

### Tarefas Trimestrais de Manutenção

- Simulação de recuperação de desastres (restauração completa do sistema)
- Revisão de otimização de custos
- Benchmarking de performance
- Atualização de documentação

---

## Apêndice A: Melhores Práticas de Segurança

### Segurança de Rede

- Usar VPC com sub-redes privadas para tasks ECS e instâncias EC2
- Restringir security groups (permitir apenas portas necessárias)
- Habilitar VPC Flow Logs para análise de tráfego
- Usar AWS WAF (Web Application Firewall) no ALB
- Habilitar proteção DDoS via AWS Shield

### Segurança de Dados

- Criptografar volumes EFS em repouso (AWS KMS)
- Criptografar buckets S3 em repouso e em trânsito
- Habilitar versionamento e MFA delete em buckets S3
- Usar roles IAM (evitar credenciais hardcoded)
- Rotacionar credenciais trimestralmente (Secrets Manager)

### Segurança de Aplicação

- Implementar rate limiting (API Gateway ou middleware customizado)
- Validar todos os parâmetros de entrada (prevenir SQL injection, XSS)
- Usar políticas CORS (restringir a domínios frontend)
- Habilitar apenas HTTPS (redirecionar HTTP para HTTPS)
- Implementar autenticação de API (JWT ou chaves API)

### Conformidade

- LGPD: Se processar dados de cidadãos brasileiros, garantir conformidade de residência de dados
- HIPAA: Se dados relacionados à saúde, usar serviços AWS elegíveis para HIPAA
- SOC 2: Auditorias regulares para provedores de serviços

---

## Apêndice B: Guia de Troubleshooting

### Problema: Alta Latência da API

**Sintomas**: Tempos de resposta da API >5 segundos

**Diagnóstico**:
1. Verificar métricas CloudWatch para picos de CPU/Memória
2. Verificar throughput EFS (pode estar limitado)
3. Verificar tempos de resposta do GeoServer

**Solução**:
- Escalar tasks ECS (escalonamento horizontal)
- Fazer upgrade do EFS para modo de Throughput Provisionado
- Otimizar estilos e caching do GeoServer

### Problema: Falhas no Processamento de Dados

**Sintomas**: Fluxos Prefect falhando repetidamente

**Diagnóstico**:
1. Verificar logs Prefect no CloudWatch
2. Verificar disponibilidade de APIs externas (ERA5, NASA)
3. Verificar espaço em disco EFS

**Solução**:
- Repetir fluxos manualmente após corrigir causa raiz
- Aumentar timeout de task se downloads estiverem lentos
- Limpar arquivos temporários `/raw`

### Problema: GeoServer Não Renderiza Tiles

**Sintomas**: Requisições WMS retornam erros 500

**Diagnóstico**:
1. Verificar logs GeoServer: `/opt/geoserver/logs/`
2. Verificar se arquivos GeoTIFF estão acessíveis no EFS
3. Verificar REST API do GeoServer: `/geoserver/rest/about/version`

**Solução**:
- Reiniciar GeoServer: `sudo systemctl restart geoserver`
- Reindexar stores ImageMosaic via REST API
- Verificar permissões de arquivos no mount EFS

---

## Apêndice C: Contato e Suporte

### Suporte Técnico

- **Contato Principal**: [Seu Nome]
- **Email**: suporte@sua-empresa.com.br
- **Telefone**: +55 XX XXXX-XXXX
- **Horário Comercial**: Segunda a Sexta, 9h - 18h (Horário de Brasília)

### Caminho de Escalação

1. **Nível 1**: Problemas Frontend/API → Desenvolvedor Frontend
2. **Nível 2**: Problemas Backend/Infraestrutura → Engenheiro DevOps
3. **Nível 3**: Problemas qualidade/processamento dados → Engenheiro de Dados
4. **Nível 4**: Decisões de arquitetura → Arquiteto de Soluções

### Acordo de Nível de Serviço (SLA)

- **Problemas Críticos** (sistema fora do ar): Resposta em 1 hora, resolução em 4 horas
- **Alta Prioridade** (funcionalidade importante quebrada): Resposta em 4 horas, resolução em 24 horas
- **Média Prioridade** (bug menor): Resposta em 24 horas, resolução em 3 dias
- **Baixa Prioridade** (solicitação de melhoria): Resposta em 1 semana

---

## Histórico de Versões do Documento

| Versão | Data | Autor | Alterações |
|---------|------|--------|---------|
| 1.0 | 04/12/2025 | [Seu Nome] | Documento inicial |

---

**Fim do Documento**
