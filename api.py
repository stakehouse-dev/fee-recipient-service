# Core API for the application

from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pickle
import asyncio
import json
from sqlalchemy import MetaData
from configuration.database_configuration import engine, Base, etl_engine, ETL_Base
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
templates = Jinja2Templates(directory="templates")

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3001",
    "*", # Allow all origins
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from services.scheduler.scheduler_service import Scheduler
from services.data.beacon_chain_event_service import BeaconChainEventService
from endpoints import EndPoints

endpoints = EndPoints(app)

Base.metadata.create_all(bind=engine)
