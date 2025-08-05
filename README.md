geospatial_backend/
├── .env                     # Environment variables
├── requirements.txt          # Python dependencies
├── Makefile                 # Common tasks (testing, deployment)
├── README.md                # Project documentation
│
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── settings.py          # App settings (from environment)
│   ├── data_types.py        # Data type configurations
│   └── geoserver.py         # GeoServer-specific configs
│
├── api/                     # FastAPI application
│   ├── __init__.py
│   ├── main.py              # App factory and routes
│   ├── dependencies.py      # Shared dependencies (auth, DB)
│   ├── errors.py            # Custom HTTP exceptions
│   │
│   ├── routers/             # Route definitions
│   │   ├── data.py          # Data endpoints (WMS/WCS)
│   │   ├── processing.py    # Geospatial processing
│   │   ├── auth.py          # Authentication
│   │   └── admin.py         # Admin endpoints
│   │
│   └── schemas/             # Pydantic models
│       ├── base.py          # Common schemas
│       ├── geospatial.py    # Geospatial data models
│       └── responses.py     # API response models
│
├── core/                    # Business logic
│   ├── services/
│   │   ├── geoserver.py     # GeoServer API client
│   │   ├── data_loader.py   # Data ingestion service
│   │   ├── processing.py    # Geospatial analysis
│   │   └── cache.py         # Caching layer
│   │
│   └── models/              # Database models
│       ├── base.py          # Base SQLAlchemy model
│       ├── users.py         # User accounts
│       └── datasets.py      # Data catalog
│
├── db/                      # Database management
│   ├── migrations/          # Alembic migrations
│   ├── fixtures/            # Test data
│   └── session.py           # Database session factory
│
├── utils/                   # Shared utilities
│   ├── geospatial.py        # GIS helper functions
│   ├── logging.py           # Logging config
│   └── security.py          # Auth utilities
│
├── tests/                   # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py          # Pytest fixtures
│
└── scripts/                 # Utility scripts
    ├── deploy/              # Deployment scripts
    ├── data_processing/     # ETL pipelines
    └── geoserver_setup.py   # GeoServer config scripts