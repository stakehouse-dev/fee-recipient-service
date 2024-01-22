from configuration.database_configuration import Base
from sqlalchemy import Column, DateTime, BigInteger, Integer, String, func


class LSD(Base):
    __tablename__ = "lsd"

    lsd_index = Column(BigInteger, primary_key=True, nullable=False, index=True)
    id = Column(String(50), nullable=False, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    fee_recipient_and_syndicate = Column(String(255), nullable=False)

    created_datetime = Column(DateTime, default=func.now())
    updated_datetime = Column(DateTime, default=func.now(), onupdate=func.now())