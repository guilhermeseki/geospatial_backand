# Arquitetura de Infraestrutura em Nuvem
## Plataforma de Dados Climáticos Geoespaciais

---

## Sumário Executivo

Este documento especifica a arquitetura de infraestrutura em nuvem para implantação da Plataforma de API de Dados Climáticos Geoespaciais na Amazon Web Services (AWS). O sistema foi projetado para alta disponibilidade, escalabilidade automática e custos otimizados.

---

## 1. Visão Geral da Arquitetura

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERNET                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │CloudFront│ (CDN Global)
                    │Route 53  │ (DNS)
                    └────┬────┘
                         │
            ┌────────────┴────────────┐
            │                         │
       ┌────▼─────┐            ┌─────▼────┐
       │   ALB    │            │   ALB    │
       │ FastAPI  │            │GeoServer │
       └────┬─────┘            └─────┬────┘
            │                         │
     ┌──────┴──────┐           ┌─────┴─────┐
     │             │           │           │
┌────▼────┐   ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
│ECS Task │   │ECS Task│ │EC2     │ │EC2     │
│FastAPI  │   │FastAPI │ │GeoServer│ │GeoServer│
│Primary  │   │Replica │ │Primary │ │Standby │
└────┬────┘   └───┬────┘ └───┬────┘ └───┬────┘
     │            │           │           │
     └────────┬───┴───────────┴───────────┘
              │
         ┌────▼──────────────────┐
         │   Amazon EFS (NFS)    │
         │  100GB+ Multi-AZ      │
         └────┬──────────────────┘
              │
         ┌────▼────┐
         │   S3    │
         │ Backups │
         └─────────┘

┌─────────────────────────────────────────┐
│  ECS Fargate - Processamento Prefect    │
│  (Agendado via EventBridge)             │
└─────────────────────────────────────────┘
```

---

## 2. Especificações Detalhadas da Infraestrutura

### 2.1 Rede e Segurança

#### VPC (Virtual Private Cloud)
```yaml
Configuração:
  CIDR: 10.0.0.0/16
  Regiões: us-east-1 (primária)
  Zonas de Disponibilidade: 2 (us-east-1a, us-east-1b)

Sub-redes:
  Públicas (DMZ):
    - 10.0.1.0/24 (us-east-1a) - ALB, NAT Gateway
    - 10.0.2.0/24 (us-east-1b) - ALB, NAT Gateway

  Privadas (Aplicação):
    - 10.0.10.0/24 (us-east-1a) - ECS Tasks, EC2
    - 10.0.11.0/24 (us-east-1b) - ECS Tasks, EC2

  Privadas (Dados):
    - 10.0.20.0/24 (us-east-1a) - EFS Mount Target
    - 10.0.21.0/24 (us-east-1b) - EFS Mount Target
```

#### Security Groups

**SG-ALB-FastAPI**
```
Inbound:
  - 443/TCP de 0.0.0.0/0 (HTTPS público)
  - 80/TCP de 0.0.0.0/0 (redirect para HTTPS)

Outbound:
  - 8000/TCP para SG-ECS-FastAPI
```

**SG-ALB-GeoServer**
```
Inbound:
  - 443/TCP de 0.0.0.0/0
  - 8080/TCP de SG-ECS-FastAPI (consultas internas)

Outbound:
  - 8080/TCP para SG-EC2-GeoServer
```

**SG-ECS-FastAPI**
```
Inbound:
  - 8000/TCP de SG-ALB-FastAPI

Outbound:
  - 443/TCP para 0.0.0.0/0 (APIs externas)
  - 2049/TCP para SG-EFS (NFS)
  - 8080/TCP para SG-ALB-GeoServer
```

**SG-EC2-GeoServer**
```
Inbound:
  - 8080/TCP de SG-ALB-GeoServer
  - 22/TCP de VPN ou Bastion Host (administração)

Outbound:
  - 2049/TCP para SG-EFS
  - 443/TCP para 0.0.0.0/0 (atualizações)
```

**SG-EFS**
```
Inbound:
  - 2049/TCP de SG-ECS-FastAPI
  - 2049/TCP de SG-EC2-GeoServer

Outbound:
  - Nenhuma (não necessária)
```

---

### 2.2 Camada de Computação

#### Application Load Balancer (ALB)

**ALB-FastAPI**
```yaml
Tipo: Application Load Balancer
Scheme: internet-facing
Subnets: Sub-redes públicas (multi-AZ)
Security Group: SG-ALB-FastAPI

Listeners:
  - Porta 80 (HTTP):
      Action: Redirect para HTTPS 443

  - Porta 443 (HTTPS):
      Certificado: ACM (api.empresa.com.br)
      Target Group: TG-FastAPI
      Health Check:
        Path: /health
        Interval: 30s
        Timeout: 5s
        Healthy Threshold: 2
        Unhealthy Threshold: 3

Sticky Sessions: Desabilitado
Connection Draining: 30 segundos
```

**ALB-GeoServer**
```yaml
Tipo: Application Load Balancer
Scheme: internet-facing
Subnets: Sub-redes públicas (multi-AZ)
Security Group: SG-ALB-GeoServer

Listeners:
  - Porta 443 (HTTPS):
      Certificado: ACM (maps.empresa.com.br)
      Target Group: TG-GeoServer
      Health Check:
        Path: /geoserver/rest/about/version.json
        Interval: 30s
        Timeout: 10s
        Healthy Threshold: 2
        Unhealthy Threshold: 2

Sticky Sessions: Habilitado (1 hora)
Connection Draining: 60 segundos
```

---

#### ECS Fargate (FastAPI)

**Cluster ECS**
```yaml
Nome: geospatial-api-cluster
Tipo: FARGATE
Container Insights: Habilitado
```

**Service: FastAPI**
```yaml
Launch Type: FARGATE
Platform Version: LATEST

Task Definition:
  Family: fastapi-app
  Network Mode: awsvpc
  CPU: 2048 (2 vCPU)
  Memory: 8192 MB (8 GB)

  Container:
    Nome: fastapi-container
    Image: ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/fastapi-app:latest
    Port Mappings:
      - 8000:8000/tcp

    Environment Variables:
      - DATA_DIR=/mnt/efs/geoserver_data
      - GEOSERVER_URL=https://maps.empresa.com.br
      - LOG_LEVEL=INFO

    Secrets (AWS Secrets Manager):
      - NASA_EARTHDATA_USERNAME
      - NASA_EARTHDATA_PASSWORD
      - COPERNICUS_API_KEY

    Mount Points:
      - Source: efs-geoserver-data
        Container Path: /mnt/efs
        ReadOnly: false

    Health Check:
      Command: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      Interval: 30s
      Timeout: 5s
      Retries: 3

    Logging:
      Driver: awslogs
      Options:
        awslogs-group: /ecs/fastapi-app
        awslogs-region: us-east-1
        awslogs-stream-prefix: ecs

Service Configuration:
  Desired Count: 2
  Min Healthy Percent: 50
  Max Percent: 200

  Network:
    Subnets: Sub-redes privadas (app)
    Security Groups: SG-ECS-FastAPI
    Assign Public IP: Não

  Load Balancer:
    Target Group: TG-FastAPI
    Container: fastapi-container
    Port: 8000

  Auto Scaling:
    Min Tasks: 2
    Max Tasks: 10

    Target Tracking Policies:
      - Métrica: ECSServiceAverageCPUUtilization
        Target: 70%
        Scale Out Cooldown: 60s
        Scale In Cooldown: 300s

      - Métrica: ALBRequestCountPerTarget
        Target: 1000
        Scale Out Cooldown: 60s
        Scale In Cooldown: 180s
```

---

#### EC2 (GeoServer)

**Instância Primary**
```yaml
Instance Type: m5.2xlarge
  vCPUs: 8
  Memory: 32 GB
  Network: Up to 10 Gbps
  EBS: Optimized

AMI: Ubuntu 22.04 LTS
Region: us-east-1a

Storage:
  Root Volume:
    Type: gp3
    Size: 50 GB
    IOPS: 3000
    Throughput: 125 MB/s
    Encrypted: Yes (KMS)

Network:
  Subnet: Sub-rede privada (us-east-1a)
  Security Group: SG-EC2-GeoServer
  Private IP: 10.0.10.10 (estático)
  Public IP: Não

IAM Role:
  - AmazonSSMManagedInstanceCore (Session Manager)
  - CloudWatchAgentServerPolicy
  - EFS mount permissions

User Data (Startup Script):
  - Instalar Java 17
  - Instalar GeoServer 2.24+
  - Montar EFS: /mnt/geoserver_data
  - Configurar systemd service
  - Configurar JVM: -Xms24g -Xmx24g

Monitoring:
  CloudWatch Agent: Habilitado
  Detailed Monitoring: Sim
```

**Instância Standby**
```yaml
[Mesma configuração da Primary]
Region: us-east-1b
Private IP: 10.0.11.10
```

**Target Group GeoServer**
```yaml
Health Check:
  Protocol: HTTP
  Path: /geoserver/rest/about/version.json
  Port: 8080
  Interval: 30s
  Timeout: 10s
  Healthy Threshold: 2
  Unhealthy Threshold: 2

Configuração:
  - Primary recebe tráfego por padrão
  - Standby entra automaticamente se Primary falhar health check
```

---

### 2.3 Armazenamento

#### Amazon EFS (Elastic File System)

```yaml
Nome: geoserver-data-efs
Performance Mode: General Purpose
Throughput Mode: Bursting
  - Baseline: 50 MB/s por TB
  - Burst: 100 MB/s

Storage Class:
  - Standard: Dados acessados frequentemente
  - Infrequent Access (IA): Após 30 dias (opcional)

Encryption:
  At Rest: Sim (AWS KMS)
  In Transit: Sim (TLS)

Backup:
  AWS Backup: Daily at 02:00 UTC
  Retention: 30 days

Mount Targets:
  - us-east-1a: 10.0.20.50
  - us-east-1b: 10.0.21.50
  Security Group: SG-EFS

Access Points:
  - /geoserver_data
    - POSIX User: 1000:1000
    - Permissions: 755

Lifecycle Management:
  - Move to IA after 30 days: Enabled
```

**Estrutura de Diretórios EFS:**
```
/geoserver_data/
├── chirps/              (~60 GB - GeoTIFFs 2018-2025)
├── chirps_hist/         (~500 MB - NetCDF histórico)
├── merge/               (~40 GB - GeoTIFFs 2018-2025)
├── merge_hist/          (~400 MB - NetCDF histórico)
├── temp_max/            (~50 GB - GeoTIFFs ERA5)
├── temp_max_hist/       (~600 MB - NetCDF)
├── temp_min/            (~50 GB - GeoTIFFs ERA5)
├── temp_min_hist/       (~600 MB - NetCDF)
├── temp/                (~50 GB - GeoTIFFs ERA5 mean)
├── temp_hist/           (~600 MB - NetCDF)
├── glm_fed/             (~200 MB - GeoTIFFs raios)
├── glm_fed_hist/        (~122 MB - NetCDF)
├── ndvi_s2/             (~30 GB - Sentinel-2)
├── ndvi_s2_hist/        (~400 MB - NetCDF)
├── ndvi_modis/          (~20 GB - MODIS)
├── ndvi_modis_hist/     (~300 MB - NetCDF)
└── raw/                 (cache temporário, limpar semanalmente)

Total Estimado: ~300 GB
```

---

#### Amazon S3 (Backups e Archive)

**Bucket: geospatial-data-backup**
```yaml
Region: us-east-1
Versioning: Enabled (3 versões)
Encryption: SSE-S3

Lifecycle Policies:
  - Rule 1 (NetCDF Current):
      Prefix: netcdf/current/
      Actions:
        - Move to Standard-IA after 90 days
        - Move to Glacier after 1 year

  - Rule 2 (NetCDF Historical):
      Prefix: netcdf/historical/
      Actions:
        - Move to Glacier immediately

  - Rule 3 (Raw Downloads):
      Prefix: raw/
      Actions:
        - Delete after 7 days

Replication:
  Destination: us-west-2 (opcional, compliance)
  Storage Class: Standard-IA

Access Control:
  Block Public Access: Yes
  Bucket Policy: IAM only
```

---

### 2.4 Processamento de Dados

#### ECS Fargate (Prefect)

**Service: Prefect Workers**
```yaml
Cluster: geospatial-processing-cluster

Task Definitions:

  1. ERA5 Temperature:
      CPU: 2048 (2 vCPU)
      Memory: 16384 MB (16 GB)
      Timeout: 4 hours
      Storage: 50 GB ephemeral

  2. CHIRPS/MERGE Precipitation:
      CPU: 2048 (2 vCPU)
      Memory: 8192 MB (8 GB)
      Timeout: 2 hours
      Storage: 30 GB ephemeral

  3. GLM Lightning:
      CPU: 4096 (4 vCPU)
      Memory: 16384 MB (16 GB)
      Timeout: 6 hours
      Storage: 100 GB ephemeral
      Environment:
        - MAX_DOWNLOAD_WORKERS=8

  4. NDVI (Sentinel-2 / MODIS):
      CPU: 2048 (2 vCPU)
      Memory: 8192 MB (8 GB)
      Timeout: 3 hours
      Storage: 40 GB ephemeral

Scheduling (EventBridge):
  - ERA5: cron(0 2 * * ? *) - Diário 02:00 UTC
  - CHIRPS: cron(0 3 * * ? *) - Diário 03:00 UTC
  - MERGE: cron(0 4 * * ? *) - Diário 04:00 UTC
  - GLM: cron(0 5 * * ? *) - Diário 05:00 UTC
  - NDVI: cron(0 3 ? * SUN *) - Domingo 03:00 UTC

Logging:
  CloudWatch Log Group: /ecs/prefect-flows
  Retention: 30 days
```

---

### 2.5 CDN e DNS

#### Amazon CloudFront

**Distribution: API**
```yaml
Origin: ALB-FastAPI
Domain: api.empresa.com.br

Cache Behaviors:
  - Path: /api/*
      Cache Policy: Disabled
      Origin Request Policy: AllViewer
      Compress: Yes

  - Path: /health
      Cache Policy: Disabled
      TTL: 0

SSL Certificate: ACM (api.empresa.com.br)
Viewer Protocol: Redirect HTTP to HTTPS
HTTP Versions: HTTP/2, HTTP/3
Geographic Restrictions: None
```

**Distribution: Maps**
```yaml
Origin: ALB-GeoServer
Domain: maps.empresa.com.br

Cache Behaviors:
  - Path: /*/wms*
      Cache Policy: CachingOptimized
      TTL: Min=3600s, Default=3600s, Max=86400s
      Query Strings: All
      Compress: Yes

  - Path: /geoserver/gwc/*
      Cache Policy: CachingOptimized
      TTL: Min=86400s, Default=604800s, Max=2592000s
      Compress: Yes

SSL Certificate: ACM (maps.empresa.com.br)
Viewer Protocol: Redirect HTTP to HTTPS
```

#### Route 53

```yaml
Hosted Zone: empresa.com.br

Records:
  - api.empresa.com.br
      Type: A (Alias)
      Target: CloudFront Distribution (API)

  - maps.empresa.com.br
      Type: A (Alias)
      Target: CloudFront Distribution (Maps)

  - internal-alb-geoserver.empresa.com.br
      Type: A (Alias)
      Target: ALB-GeoServer (Private)
      Routing: Private Zone

Health Checks:
  - api.empresa.com.br/health
      Protocol: HTTPS
      Interval: 30s
      Alarm: SNS → Email
```

---

### 2.6 Monitoramento e Logs

#### CloudWatch

**Métricas Customizadas**
```yaml
Namespace: Geospatial/API

Métricas:
  - APIResponseTime (ms)
      Dimensions: [Endpoint, Method, StatusCode]
      Statistics: Average, p50, p95, p99

  - APIRequestCount
      Dimensions: [Endpoint, Method, StatusCode]
      Statistics: Sum

  - DataProcessingDuration (minutes)
      Dimensions: [FlowName, Date]
      Statistics: Average, Max

  - EFSThroughput (MB/s)
      Dimensions: [MountTarget]
      Statistics: Average, Max
```

**Alarmes**
```yaml
Alarmes Críticos (SNS → PagerDuty):
  1. API-Error-Rate-High:
       Métrica: HTTPCode_Target_5XX_Count (ALB)
       Threshold: > 50 em 5 minutos
       Action: Escalar tasks ECS + Notificar

  2. ECS-Task-Failure:
       Métrica: TasksFailed
       Threshold: > 2 em 5 minutos
       Action: Restart service + Notificar

  3. EFS-Storage-Full:
       Métrica: EFS PercentIOLimit
       Threshold: > 80%
       Action: Notificar para expansão

  4. GeoServer-Down:
       Métrica: UnHealthyHostCount (TG-GeoServer)
       Threshold: >= 1 por 2 minutos
       Action: Restart instance + Notificar

Alarmes Warning (SNS → Email):
  1. API-Latency-High:
       Métrica: TargetResponseTime (ALB)
       Threshold: > 1000ms (p95) em 10 minutos
       Action: Revisar performance

  2. ECS-CPU-High:
       Métrica: CPUUtilization
       Threshold: > 80% por 15 minutos
       Action: Considerar scale-out

  3. Data-Processing-Delay:
       Métrica: Custom - LastSuccessfulRun
       Threshold: > 12 horas atrás
       Action: Verificar fluxos Prefect
```

**Log Groups**
```yaml
/ecs/fastapi-app:
  Retention: 30 dias
  Insights: Habilitado

/ecs/prefect-flows:
  Retention: 30 dias
  Insights: Habilitado

/aws/ec2/geoserver:
  Retention: 14 dias
  Insights: Não

/aws/lambda/processing:
  Retention: 7 dias
  Insights: Não
```

---

## 3. Estimativa de Custos (Mensal)

### Breakdown Detalhado

| Serviço | Especificação | Custo (R$) |
|---------|--------------|------------|
| **Computação** | | |
| ECS Fargate (FastAPI) | 2 tasks × 2vCPU, 8GB × 730h | R$ 600 |
| EC2 m5.2xlarge (GeoServer) | 1 instância × 730h | R$ 1.400 |
| ECS Fargate (Prefect) | 4 flows/dia × 2h × 30 dias | R$ 150 |
| **Rede** | | |
| ALB (2 instâncias) | LCU + Data processed | R$ 200 |
| CloudFront | 1 TB transferência | R$ 425 |
| Data Transfer Out | 500 GB/mês | R$ 225 |
| **Armazenamento** | | |
| EFS (300 GB) | General Purpose | R$ 450 |
| S3 Standard (500 GB) | Backups recentes | R$ 100 |
| S3 Glacier (2 TB) | Archive histórico | R$ 25 |
| EBS gp3 (50 GB) | Root EC2 | R$ 20 |
| **Serviços Gerenciados** | | |
| Route 53 | 1 hosted zone + queries | R$ 5 |
| Certificate Manager | Certificados SSL | R$ 0 |
| CloudWatch Logs | 50 GB/mês ingestão | R$ 50 |
| CloudWatch Metrics | Custom metrics | R$ 20 |
| CloudWatch Alarms | 20 alarmes | R$ 10 |
| AWS Backup | EFS snapshots diários | R$ 50 |
| Secrets Manager | 5 secrets | R$ 15 |
| **Total Estimado** | | **R$ 3.745/mês** |

### Otimizações de Custo

#### Curto Prazo (Implementação Imediata)
1. **Savings Plans** - Computação
   - Commitment: 1 ano, pagamento total adiantado
   - Economia: ~30% em ECS Fargate e EC2
   - Redução: R$ 600/mês → **Total: R$ 3.145/mês**

2. **EFS Lifecycle** - Armazenamento
   - Mover dados >30 dias para IA class
   - Economia: ~50% em 200 GB
   - Redução: R$ 150/mês → **Total: R$ 2.995/mês**

3. **CloudWatch Logs Aggregation**
   - Reduzir retenção para 7 dias (logs não críticos)
   - Economia: R$ 25/mês → **Total: R$ 2.970/mês**

#### Médio Prazo (3-6 meses)
1. **Reserved Instances** - EC2
   - 3 anos, pagamento parcial adiantado
   - Economia: ~50% em m5.2xlarge
   - Redução: R$ 700/mês → **Total: R$ 2.270/mês**

2. **Spot Instances** - Prefect Processing
   - Usar Spot para tasks não críticas
   - Economia: ~70% em processamento
   - Redução: R$ 105/mês → **Total: R$ 2.165/mês**

#### Longo Prazo (6-12 meses)
1. **S3 Intelligent Tiering** - Backups
   - Automatizar movimentação entre tiers
   - Economia: R$ 50/mês → **Total: R$ 2.115/mês**

2. **Graviton Instances** - ECS/EC2
   - Migrar para ARM (m6g.2xlarge)
   - Economia: ~20% em computação
   - Redução: R$ 350/mês → **Total: R$ 1.765/mês**

**Economia Total Potencial: R$ 1.980/mês (53%)**

---

## 4. Escalabilidade

### Cenários de Crescimento

| Tráfego | Configuração | Custo Mensal |
|---------|--------------|--------------|
| **Atual (Small)** | 2 ECS tasks, 1 EC2 | R$ 3.745 |
| **2x Crescimento** | 4 ECS tasks, 2 EC2 | R$ 6.500 |
| **5x Crescimento** | 8 ECS tasks, 2 EC2 + Cache | R$ 12.000 |
| **10x Crescimento** | 15 ECS tasks, 4 EC2 + RDS | R$ 22.000 |

### Auto-scaling Policies

**ECS FastAPI:**
```python
# Scale Out: CPU > 70% OU Requests > 1000/min
# Scale In: CPU < 30% por 5 minutos
# Cooldown: 60s (out), 300s (in)

Exemplo:
  10:00 - 2 tasks (normal)
  10:15 - CPU 80% → Adiciona 2 tasks → 4 tasks
  10:30 - CPU 75% → Adiciona 2 tasks → 6 tasks
  10:45 - CPU 60% → Mantém 6 tasks
  11:00 - CPU 25% → Aguarda cooldown (5 min)
  11:05 - CPU 25% → Remove 2 tasks → 4 tasks
  11:10 - CPU 20% → Remove 2 tasks → 2 tasks
```

---

## 5. Disaster Recovery

### RPO e RTO

| Componente | RPO | RTO | Estratégia |
|------------|-----|-----|------------|
| FastAPI (ECS) | 0 | 5 min | Multi-AZ, Auto-restart |
| GeoServer (EC2) | 0 | 10 min | Standby automático (ALB) |
| EFS Data | 24h | 1h | AWS Backup, snapshot diário |
| S3 Backups | 0 | Imediato | Multi-AZ, versionamento |
| Configuração | 0 | 30 min | Infrastructure as Code (Terraform) |

### Procedimentos de Recovery

**Cenário 1: Falha de AZ Completa**
```
1. ALB automaticamente redireciona para AZ saudável
2. ECS tasks são recriados na AZ disponível
3. EFS mount targets mudam para AZ saudável
4. Tempo estimado: 5-10 minutos
5. Sem intervenção manual necessária
```

**Cenário 2: Corrupção de Dados EFS**
```
1. Identificar último snapshot saudável no AWS Backup
2. Criar novo EFS a partir do snapshot
3. Atualizar mount targets em ECS/EC2
4. Reiniciar serviços
5. Tempo estimado: 1-2 horas
6. Perda de dados: Até 24 horas (último backup)
```

**Cenário 3: Falha Regional Completa**
```
1. Ativar região secundária (us-west-2)
2. Restaurar EFS de backup S3 cross-region
3. Lançar infraestrutura via Terraform
4. Atualizar Route 53 DNS
5. Tempo estimado: 4-8 horas
6. Requer intervenção manual
```

---

## 6. Segurança e Compliance

### Controles de Segurança

#### Camada de Rede
- ✅ VPC com sub-redes privadas isoladas
- ✅ Security Groups restritivos (princípio do menor privilégio)
- ✅ Network ACLs como camada adicional
- ✅ VPC Flow Logs habilitados (auditoria)
- ✅ AWS WAF no ALB (proteção XSS, SQL injection)
- ✅ AWS Shield Standard (proteção DDoS)

#### Camada de Aplicação
- ✅ HTTPS obrigatório (TLS 1.2+)
- ✅ Certificados SSL via ACM (renovação automática)
- ✅ Rate limiting (1000 req/min por IP)
- ✅ CORS configurado (domínios específicos)
- ✅ Headers de segurança (HSTS, X-Frame-Options)

#### Camada de Dados
- ✅ EFS criptografado em repouso (KMS)
- ✅ EFS criptografado em trânsito (TLS)
- ✅ S3 criptografado (SSE-S3)
- ✅ S3 Block Public Access habilitado
- ✅ Secrets Manager para credenciais
- ✅ IAM Roles (sem access keys hardcoded)

#### Auditoria e Compliance
- ✅ CloudTrail habilitado (todas as APIs)
- ✅ Config Rules para compliance
- ✅ GuardDuty para detecção de ameaças
- ✅ Systems Manager Session Manager (no SSH keys)
- ✅ KMS audit logs

---

## 7. Manutenção e SLAs

### SLA (Service Level Agreement)

| Métrica | Target | Penalidade |
|---------|--------|------------|
| Uptime Mensal | ≥ 99.5% | Crédito 10% |
| API Response Time (p95) | ≤ 500ms | Revisão arquitetura |
| Data Freshness | ≤ 12h atraso | Investigação |
| Incident Response | ≤ 1h | Escalação |

### Janelas de Manutenção

**Semanal** (Domingo 03:00-05:00 UTC)
- Atualizações de segurança OS
- Limpeza de cache /raw
- Verificação de logs

**Mensal** (Primeiro domingo 02:00-06:00 UTC)
- Atualização de GeoServer
- Otimização de índices EFS
- Teste de disaster recovery

**Trimestral**
- Upgrade major de dependências
- Revisão de custos e otimização
- Auditoria de segurança

---

## Apêndice: Terraform Modules

### Estrutura de Código

```
infrastructure/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── production/
├── modules/
│   ├── vpc/
│   ├── alb/
│   ├── ecs-fargate/
│   ├── ec2-geoserver/
│   ├── efs/
│   ├── cloudfront/
│   └── monitoring/
└── README.md
```

### Exemplo: Module ECS Fargate

```hcl
# modules/ecs-fargate/main.tf

resource "aws_ecs_cluster" "main" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = var.container_name
    image     = var.container_image
    essential = true

    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]

    environment = var.environment_variables
    secrets     = var.secrets

    mountPoints = [{
      sourceVolume  = "efs-storage"
      containerPath = "/mnt/efs"
      readOnly      = false
    }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  volume {
    name = "efs-storage"

    efs_volume_configuration {
      file_system_id          = var.efs_id
      transit_encryption      = "ENABLED"
      authorization_config {
        access_point_id = var.efs_access_point_id
      }
    }
  }
}

resource "aws_ecs_service" "app" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = var.container_name
    container_port   = var.container_port
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 50
  }

  depends_on = [var.alb_listener]
}

resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.max_tasks
  min_capacity       = var.min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.service_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
```

---

## Contato

**Arquiteto de Soluções:** [Seu Nome]
**Email:** arquitetura@empresa.com.br
**Telefone:** +55 XX XXXX-XXXX

---

**Versão:** 1.0
**Data:** 04/12/2025
**Status:** Aprovado para Implementação
