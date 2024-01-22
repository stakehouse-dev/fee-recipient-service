from configuration.database_configuration import Base
from sqlalchemy import Column, DateTime, BigInteger, Integer, String, func, ForeignKey
from sqlalchemy.orm import relationship, backref
from models.lsd_model import LSD


class Validator(Base):
    __tablename__ = "validator"

    id = Column(String(100), primary_key=True, nullable=False, index=True)
    index = Column(Integer, nullable=False, index=True)

    lsd_id = Column(String(50), ForeignKey(LSD.id), nullable=False, index=True)

    created_datetime = Column(DateTime, default=func.now())
    updated_datetime = Column(DateTime, default=func.now(), onupdate=func.now())
