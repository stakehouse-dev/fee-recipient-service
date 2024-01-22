from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from apiconfig import APIConfig
import json


session_options = {"autoflush": True}
config = APIConfig()


Base = declarative_base()
engine = create_engine(
    "mysql+pymysql://" + config.db("connection_string"),
    convert_unicode=True,
    pool_size=int(config.db("connection_pool_size")),
    pool_recycle=3600,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, **session_options)


ETL_Base = declarative_base()
etl_engine = create_engine(
    "mysql+pymysql://" + config.etl_db("connection_string"),
    convert_unicode=True,
    pool_size=int(config.etl_db("connection_pool_size")),
    pool_recycle=3600,
)
ETL_SessionLocal = sessionmaker(bind=etl_engine, expire_on_commit=False, **session_options)

# async_engine = create_async_engine(
#     "mysql+asyncmy://"
#     + config.db("connection_string"),
#     convert_unicode=True,
#     pool_size=int(config.db("connection_pool_size")),
#     pool_recycle=3600,
# )

# Async_Session = sessionmaker(
#     bind=async_engine, expire_on_commit=False, class_=AsyncSession
# )

# session_options = {"autoflush": True}


# Testing with SQLite
# engine = create_engine(
#     config.db("host"),
#     # convert_unicode=True,
#     # pool_size=int(config.db("connection_pool_size")),
#     # pool_recycle=3600,
#     connect_args={"check_same_thread": False},
# )
# SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, **session_options)
