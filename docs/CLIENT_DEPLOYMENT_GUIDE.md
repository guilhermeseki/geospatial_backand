# Geospatial Climate Data Platform - Deployment Guide

## Executive Summary

This document outlines the recommended cloud infrastructure architecture for deploying the Geospatial Climate Data API platform and integrating it with frontend applications. The platform provides real-time and historical climate data (precipitation, temperature, lightning, NDVI) through a high-performance REST API backed by GeoServer for map visualization.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Cloud Infrastructure Recommendations](#cloud-infrastructure-recommendations)
3. [AWS Deployment Architecture](#aws-deployment-architecture)
4. [Frontend Integration](#frontend-integration)
5. [Cost Estimates](#cost-estimates)
6. [Deployment Checklist](#deployment-checklist)
7. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 1. System Overview

### Platform Components

The platform consists of four main components:

1. **FastAPI Backend** - RESTful API serving climate data queries
2. **GeoServer** - Map tile server for WMS visualization
3. **Data Processing Pipeline** - Prefect workflows for automated data ingestion
4. **Data Storage** - NetCDF historical files + GeoTIFF mosaics

### Current Data Sources

- **Precipitation**: CHIRPS, MERGE (daily, 5km resolution)
- **Temperature**: ERA5 (min/max/mean, daily, 9km resolution)
- **Lightning**: GLM FED (GOES-16, 8km resolution, 30-min windows)
- **NDVI**: Sentinel-2 (10m), MODIS (250m, 16-day composites)

### Data Volume

- **Historical NetCDF**: ~500 MB per year per dataset
- **GeoTIFF Mosaics**: ~2 MB per day per dataset
- **Total Storage**: ~50-100 GB for complete historical archive (2018-present)
- **Daily Growth**: ~10-20 MB per day across all datasets

---

## 2. Cloud Infrastructure Recommendations

### Why Cloud Deployment?

✅ **Scalability**: Handle traffic spikes during extreme weather events
✅ **Reliability**: 99.9%+ uptime with auto-recovery
✅ **Global Access**: CDN integration for worldwide users
✅ **Cost Efficiency**: Pay only for resources used
✅ **Disaster Recovery**: Automated backups and redundancy

### Recommended Cloud Provider: **Amazon Web Services (AWS)**

**Rationale:**
- Industry-leading geospatial data services (S3, EFS, CloudFront)
- Excellent Python/FastAPI ecosystem support
- Competitive pricing for compute and storage
- Strong compliance and security certifications
- Native integration with monitoring tools

**Alternative Options:**
- **Google Cloud Platform (GCP)**: Better BigQuery integration for analytics
- **Microsoft Azure**: Better for enterprise Microsoft environments
- **DigitalOcean**: Simpler setup, lower cost for small/medium deployments

---

## 3. AWS Deployment Architecture

### Architecture Diagram

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
    │ (Task)  │                  │ (Task)  │     │ Primary │        │ Standby │
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
         │  Prefect Server (ECS Fargate) - Data Processing         │
         │  - ERA5 Temperature Flow (daily, scheduled)             │
         │  - CHIRPS Precipitation Flow (daily, scheduled)         │
         │  - GLM Lightning Flow (daily, scheduled)                │
         │  - NDVI Flows (weekly, scheduled)                       │
         └─────────────────────────────────────────────────────────┘
```

### Detailed Component Specifications

#### 3.1 Application Load Balancer (ALB)
- **Purpose**: Distribute traffic, SSL termination, health checks
- **Type**: Application Load Balancer
- **Listeners**:
  - Port 443 (HTTPS) → FastAPI containers
  - Port 8080 (HTTP) → GeoServer instances
- **SSL Certificate**: AWS Certificate Manager (free)
- **Health Check**: `/health` endpoint (FastAPI), `/geoserver/rest/about/version` (GeoServer)

#### 3.2 FastAPI Backend (ECS Fargate)
- **Service**: Elastic Container Service (ECS) with Fargate
- **Container Image**: Custom Docker image (FastAPI + dependencies)
- **Task Definition**:
  - CPU: 2 vCPU
  - Memory: 8 GB RAM
  - Container Port: 8000
- **Auto-scaling**:
  - Min: 2 tasks
  - Max: 10 tasks
  - Scale-out: CPU > 70% or Request count > 1000/min
  - Scale-in: CPU < 30% for 5 minutes
- **Environment Variables**:
  - `DATA_DIR=/mnt/efs/geoserver_data`
  - `GEOSERVER_URL=http://internal-alb-geoserver.internal:8080`
  - Database credentials (AWS Secrets Manager)

#### 3.3 GeoServer (EC2 Instances)
- **Instance Type**: `m5.2xlarge` (8 vCPU, 32 GB RAM)
- **Operating System**: Ubuntu 22.04 LTS
- **Storage**:
  - Root: 50 GB gp3 SSD
  - Data: Mount EFS at `/mnt/geoserver_data`
- **Configuration**:
  - Java Heap: 24 GB
  - GeoWebCache enabled (tile caching)
  - WMS/WFS services enabled
- **High Availability**:
  - Primary-Standby setup
  - Health checks via ALB
  - Automatic failover

#### 3.4 Shared Storage (Amazon EFS)
- **Type**: Elastic File System (NFS v4)
- **Performance Mode**: General Purpose
- **Throughput Mode**: Bursting (or Provisioned for heavy loads)
- **Storage Class**: Standard (frequent access)
- **Lifecycle Policy**: Move to Infrequent Access after 30 days (optional)
- **Backup**: AWS Backup (daily snapshots, 30-day retention)
- **Mount Path**: `/mnt/geoserver_data`
- **Directory Structure**:
  ```
  /mnt/geoserver_data/
  ├── chirps/          # CHIRPS GeoTIFF mosaics
  ├── chirps_hist/     # CHIRPS historical NetCDF
  ├── merge/           # MERGE GeoTIFF mosaics
  ├── merge_hist/      # MERGE historical NetCDF
  ├── temp_max/        # ERA5 max temp GeoTIFFs
  ├── temp_max_hist/   # ERA5 max temp NetCDF
  ├── glm_fed/         # GLM lightning GeoTIFFs
  ├── glm_fed_hist/    # GLM lightning NetCDF
  └── raw/             # Temporary download cache
  ```

#### 3.5 Backup Storage (Amazon S3)
- **Bucket**: `geospatial-climate-data-backup`
- **Purpose**:
  - Long-term archival of historical NetCDF files
  - Disaster recovery
  - Data lineage tracking
- **Lifecycle Policy**:
  - Standard storage for 90 days
  - Glacier for historical data > 1 year
- **Replication**: Cross-region replication (optional, for compliance)
- **Versioning**: Enabled (keep last 3 versions)

#### 3.6 Data Processing (Prefect on ECS Fargate)
- **Service**: ECS Fargate cluster for Prefect flows
- **Task Definitions**:
  - **ERA5 Temperature Flow**: 2 vCPU, 16 GB RAM
  - **CHIRPS/MERGE Flow**: 2 vCPU, 8 GB RAM
  - **GLM Lightning Flow**: 4 vCPU, 16 GB RAM (parallel downloads)
  - **NDVI Flows**: 2 vCPU, 8 GB RAM
- **Scheduling**: EventBridge Rules (cron)
  - Daily: 02:00 UTC (ERA5, CHIRPS, MERGE, GLM)
  - Weekly: Sunday 03:00 UTC (NDVI)
- **Storage**: Mount same EFS for output
- **Logging**: CloudWatch Logs
- **Notifications**: SNS topics for success/failure

#### 3.7 CDN & SSL (CloudFront)
- **Purpose**: Global content delivery, DDoS protection, caching
- **Cache Behaviors**:
  - `/wms*`: Cache for 1 hour (GeoServer tiles)
  - `/api/*`: No cache (dynamic data)
- **SSL**: Automatic HTTPS redirect
- **Custom Domain**: `api.your-company.com`, `maps.your-company.com`
- **Geographic Restrictions**: Optional (e.g., restrict to specific countries)

#### 3.8 Monitoring & Observability
- **CloudWatch Metrics**:
  - API response times
  - Request rates
  - Error rates
  - EFS throughput
  - Container CPU/Memory
- **CloudWatch Alarms**:
  - API error rate > 5%
  - ECS task failures
  - EFS storage > 80%
- **CloudWatch Logs**:
  - FastAPI application logs
  - GeoServer logs
  - Prefect flow logs
- **Application Performance Monitoring (APM)**:
  - AWS X-Ray for request tracing
  - Or third-party: DataDog, New Relic

---

## 4. Frontend Integration

### 4.1 Frontend Architecture Options

#### Option A: React/Next.js Web Application (Recommended)

**Technology Stack:**
- **Framework**: Next.js 14+ (React with SSR/SSG)
- **Mapping Library**: Leaflet or MapLibre GL JS
- **State Management**: React Query (for API caching)
- **UI Components**: Material-UI or Shadcn/ui
- **Charts**: Recharts or Chart.js
- **Hosting**: AWS Amplify or Vercel

**Features:**
- Interactive map with WMS layer overlays
- Time-series charts for historical data
- Location search and bookmarking
- Threshold alerts configuration
- Data export (CSV, JSON)
- Responsive design (mobile + desktop)

**Sample Integration Code:**

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

#### Option B: Mobile Application (Flutter)

**Technology Stack:**
- **Framework**: Flutter 3.x
- **Mapping**: flutter_map + MapLibre
- **HTTP Client**: dio
- **State Management**: Riverpod or Provider
- **Platforms**: iOS + Android

**Features:**
- Offline mode with cached tiles
- Push notifications for weather alerts
- GPS-based location detection
- Background data sync

#### Option C: Dashboard (Streamlit/Dash)

**Technology Stack:**
- **Framework**: Streamlit (Python) or Dash (Plotly)
- **Visualization**: Plotly, Folium
- **Hosting**: AWS App Runner or EC2

**Use Case**: Internal analytics dashboard, proof-of-concept

### 4.2 API Integration Examples

#### Authentication (if enabled)

```javascript
// utils/api.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${process.env.API_KEY}` // Optional
  }
});

export default apiClient;
```

#### Fetch Historical Precipitation

```javascript
// services/precipitation.js
import apiClient from '@/utils/api';

export const fetchPrecipitationHistory = async (params) => {
  const response = await apiClient.post('/precipitation/history', {
    lat: params.lat,
    lon: params.lon,
    start_date: params.startDate,
    end_date: params.endDate,
    source: params.source || 'chirps'
  });

  return response.data;
};
```

#### Fetch Temperature Triggers

```javascript
// services/temperature.js
export const fetchTemperatureTriggers = async (params) => {
  const response = await apiClient.post('/temperature/triggers', {
    lat: params.lat,
    lon: params.lon,
    start_date: params.startDate,
    end_date: params.endDate,
    threshold: params.threshold,
    operator: params.operator, // 'gt', 'lt', 'gte', 'lte'
    variable: params.variable, // 'temp_max', 'temp_min', 'temp'
    source: 'era5'
  });

  return response.data;
};
```

#### Display WMS Map Layer

```javascript
// components/MapView.jsx
import React, { useState } from 'react';
import { MapContainer, TileLayer, WMSTileLayer } from 'react-leaflet';

export default function MapView() {
  const [date, setDate] = useState('2025-11-30');
  const [layer, setLayer] = useState('chirps');

  return (
    <div>
      <div className="controls">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <select value={layer} onChange={(e) => setLayer(e.target.value)}>
          <option value="chirps">CHIRPS Precipitation</option>
          <option value="merge">MERGE Precipitation</option>
          <option value="temp_max">ERA5 Max Temperature</option>
          <option value="glm_fed">GLM Lightning</option>
        </select>
      </div>

      <MapContainer center={[-15, -55]} zoom={4} style={{ height: '600px' }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <WMSTileLayer
          url={`${process.env.NEXT_PUBLIC_API_URL}/${layer}/wms`}
          layers={layer}
          format="image/png"
          transparent={true}
          time={date}
        />
      </MapContainer>
    </div>
  );
}
```

### 4.3 Frontend Hosting Recommendations

#### AWS Amplify (Recommended for React/Next.js)
- **Auto-deploy**: Git integration (push to deploy)
- **SSL**: Free HTTPS certificates
- **CDN**: Global CloudFront distribution
- **Environment Variables**: Secure config management
- **Cost**: ~$15-50/month (based on traffic)

#### Vercel (Alternative)
- **Next.js optimized**: Best performance for Next.js apps
- **Serverless functions**: Built-in API routes
- **Edge caching**: Ultra-fast global delivery
- **Cost**: Free tier available, Pro $20/month

#### AWS S3 + CloudFront (Static Sites)
- **Cost-effective**: ~$1-5/month for small sites
- **Simple deployment**: `aws s3 sync build/ s3://bucket`
- **Best for**: Pure static sites (no SSR)

---

## 5. Cost Estimates

### Monthly AWS Cost Breakdown (Medium Traffic)

| Service | Specification | Monthly Cost (USD) |
|---------|--------------|-------------------|
| **ECS Fargate (FastAPI)** | 2 tasks × 2 vCPU, 8GB, 24/7 | $120 |
| **EC2 (GeoServer)** | 1× m5.2xlarge, 24/7 | $280 |
| **EFS Storage** | 100 GB, General Purpose | $30 |
| **S3 Backup** | 500 GB Standard + 2 TB Glacier | $25 |
| **Application Load Balancer** | 2× ALBs | $40 |
| **CloudFront (CDN)** | 1 TB data transfer | $85 |
| **CloudWatch Logs/Metrics** | Standard monitoring | $20 |
| **Data Transfer Out** | 500 GB/month | $45 |
| **Prefect Flows (ECS)** | 4 daily tasks, 2 hours avg | $30 |
| **RDS PostgreSQL** (optional) | db.t3.medium | $60 |
| **AWS Backup** | Daily EFS snapshots | $10 |
| **Route 53 DNS** | 1 hosted zone | $1 |
| **Total** | | **~$750/month** |

### Cost Optimization Tips

1. **Reserved Instances**: Save 30-40% on EC2 with 1-year commitment
2. **Spot Instances**: Use for Prefect data processing (save 70%)
3. **EFS Infrequent Access**: Move old data to IA storage class
4. **S3 Intelligent Tiering**: Automatic cost optimization
5. **CloudWatch Metrics**: Reduce retention from 15 months to 3 months
6. **Right-sizing**: Monitor and downsize overprovisioned resources

### Traffic Scaling Scenarios

| Scenario | Users/Day | API Calls/Day | Monthly Cost |
|----------|-----------|---------------|--------------|
| **Small** | <1,000 | <10,000 | $300-500 |
| **Medium** | 1,000-10,000 | 10,000-100,000 | $750-1,500 |
| **Large** | 10,000-100,000 | 100,000-1M | $2,000-5,000 |
| **Enterprise** | >100,000 | >1M | $5,000+ |

---

## 6. Deployment Checklist

### Phase 1: Infrastructure Setup (Week 1)

- [ ] Create AWS account and set up billing alerts
- [ ] Set up VPC with public/private subnets (multi-AZ)
- [ ] Create EFS file system and mount targets
- [ ] Set up S3 buckets for backups and Terraform state
- [ ] Configure IAM roles and policies (least privilege)
- [ ] Create ECR repositories for Docker images
- [ ] Set up Application Load Balancers (FastAPI + GeoServer)
- [ ] Request SSL certificates via AWS Certificate Manager
- [ ] Configure Route 53 DNS (if using custom domain)

### Phase 2: Application Deployment (Week 2)

- [ ] Build and push Docker images to ECR
  - [ ] FastAPI application image
  - [ ] Prefect worker image
- [ ] Deploy GeoServer on EC2 instances
  - [ ] Install Java 11/17
  - [ ] Configure GeoServer with optimized JVM settings
  - [ ] Mount EFS and configure data directories
  - [ ] Set up GeoWebCache for tile caching
- [ ] Deploy FastAPI via ECS Fargate
  - [ ] Create task definitions
  - [ ] Configure auto-scaling policies
  - [ ] Set environment variables (Secrets Manager)
- [ ] Deploy Prefect server on ECS
  - [ ] Set up Prefect database (RDS or external)
  - [ ] Register flows and schedules
- [ ] Configure CloudWatch monitoring and alarms

### Phase 3: Data Migration (Week 3)

- [ ] Upload historical NetCDF files to EFS (use DataSync or rsync)
- [ ] Upload GeoTIFF mosaics to EFS
- [ ] Verify GeoServer can read ImageMosaic stores
- [ ] Test API endpoints with sample data
- [ ] Run initial data processing flows
  - [ ] ERA5 temperature (last 30 days)
  - [ ] CHIRPS precipitation (last 30 days)
  - [ ] GLM lightning (last 30 days)
- [ ] Verify WMS layers render correctly

### Phase 4: Frontend Integration (Week 4)

- [ ] Set up frontend repository (GitHub/GitLab)
- [ ] Configure environment variables (API URLs, keys)
- [ ] Implement API integration layer
- [ ] Build map visualization components
- [ ] Build data query forms and charts
- [ ] Set up CI/CD pipeline (GitHub Actions or AWS CodePipeline)
- [ ] Deploy frontend to AWS Amplify or Vercel
- [ ] Configure custom domain and SSL

### Phase 5: Testing & Go-Live (Week 5)

- [ ] Load testing (Apache JMeter or Locust)
- [ ] Security audit (penetration testing, OWASP)
- [ ] Documentation review
- [ ] User acceptance testing (UAT)
- [ ] Disaster recovery drill (restore from backup)
- [ ] Performance optimization based on monitoring
- [ ] Go-live announcement and training
- [ ] Post-launch monitoring (first 48 hours)

---

## 7. Monitoring & Maintenance

### Key Performance Indicators (KPIs)

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| API Response Time (p95) | <500ms | Scale out ECS tasks |
| API Error Rate | <1% | Check logs, restart services |
| Data Processing Lag | <6 hours | Increase Prefect workers |
| EFS Throughput | <80% capacity | Upgrade to Provisioned Throughput |
| GeoServer Tile Rendering | <2s | Optimize styles, increase cache |

### Daily Monitoring Tasks

- Check CloudWatch dashboard for anomalies
- Review Prefect flow runs (success/failure)
- Monitor EFS storage usage
- Check API error logs

### Weekly Maintenance Tasks

- Review cost and usage reports
- Update security patches (OS, dependencies)
- Check backup integrity
- Review and optimize slow queries

### Monthly Maintenance Tasks

- Review and update auto-scaling policies
- Analyze traffic patterns and adjust resources
- Update datasets (e.g., new NDVI composites)
- Security audit and compliance check

### Quarterly Maintenance Tasks

- Disaster recovery drill (full system restore)
- Cost optimization review
- Performance benchmarking
- Update documentation

---

## Appendix A: Security Best Practices

### Network Security

- Use VPC with private subnets for ECS tasks and EC2 instances
- Restrict security groups (allow only necessary ports)
- Enable VPC Flow Logs for traffic analysis
- Use AWS WAF (Web Application Firewall) on ALB
- Enable DDoS protection via AWS Shield

### Data Security

- Encrypt EFS volumes at rest (AWS KMS)
- Encrypt S3 buckets at rest and in transit
- Enable S3 bucket versioning and MFA delete
- Use IAM roles (avoid hardcoded credentials)
- Rotate credentials quarterly (Secrets Manager)

### Application Security

- Implement rate limiting (API Gateway or custom middleware)
- Validate all input parameters (prevent SQL injection, XSS)
- Use CORS policies (restrict to frontend domains)
- Enable HTTPS only (redirect HTTP to HTTPS)
- Implement API authentication (JWT or API keys)

### Compliance

- GDPR: If processing EU citizen data, ensure data residency compliance
- HIPAA: If health-related data, use HIPAA-eligible AWS services
- SOC 2: Regular audits for service providers

---

## Appendix B: Troubleshooting Guide

### Issue: High API Latency

**Symptoms**: API response times >5 seconds

**Diagnosis**:
1. Check CloudWatch metrics for CPU/Memory spikes
2. Check EFS throughput (may be throttled)
3. Check GeoServer response times

**Solution**:
- Scale out ECS tasks (horizontal scaling)
- Upgrade EFS to Provisioned Throughput mode
- Optimize GeoServer styles and caching

### Issue: Data Processing Failures

**Symptoms**: Prefect flows failing repeatedly

**Diagnosis**:
1. Check Prefect logs in CloudWatch
2. Check external API availability (ERA5, NASA)
3. Check EFS disk space

**Solution**:
- Retry flows manually after fixing root cause
- Increase task timeout if downloads are slow
- Clean up `/raw` temporary files

### Issue: GeoServer Not Rendering Tiles

**Symptoms**: WMS requests return 500 errors

**Diagnosis**:
1. Check GeoServer logs: `/opt/geoserver/logs/`
2. Check if GeoTIFF files are accessible on EFS
3. Check GeoServer REST API: `/geoserver/rest/about/version`

**Solution**:
- Restart GeoServer: `sudo systemctl restart geoserver`
- Reindex ImageMosaic stores via REST API
- Check file permissions on EFS mount

---

## Appendix C: Contact & Support

### Technical Support

- **Primary Contact**: [Your Name]
- **Email**: support@your-company.com
- **Phone**: +1-XXX-XXX-XXXX
- **Business Hours**: Monday-Friday, 9 AM - 6 PM (Local Time)

### Escalation Path

1. **Level 1**: Frontend/API issues → Frontend Developer
2. **Level 2**: Backend/Infrastructure issues → DevOps Engineer
3. **Level 3**: Data quality/processing issues → Data Engineer
4. **Level 4**: Architecture decisions → Solutions Architect

### Service Level Agreement (SLA)

- **Critical Issues** (system down): 1-hour response, 4-hour resolution
- **High Priority** (major feature broken): 4-hour response, 24-hour resolution
- **Medium Priority** (minor bug): 24-hour response, 3-day resolution
- **Low Priority** (enhancement request): 1-week response

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-04 | [Your Name] | Initial document |

---

**End of Document**
