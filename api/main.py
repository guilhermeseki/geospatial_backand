from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import data, precipitation

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(precipitation.router)