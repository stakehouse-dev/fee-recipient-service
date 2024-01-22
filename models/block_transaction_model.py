from configuration.database_configuration import Base
from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    String,
    func,
)


class BlockTransaction(Base):
    __tablename__ = "block_transactions"
 
    tx_hash = Column(String(255), primary_key=True, nullable=False, index=True)
    slot = Column(BigInteger, nullable=False, index=True)
    block_hash = Column(String(255), nullable=False, index=True)
    block_number = Column(BigInteger, nullable=False, index=True)
    to = Column(String(255), nullable=False, index=True)
    sender = Column(String(255), nullable=False, index=True)
    value = Column(String(255), nullable=False, index=True)
    gas = Column(String(100), nullable=False, index=True)

    created_datetime = Column(DateTime, default=func.now())
    updated_datetime = Column(DateTime, default=func.now(), onupdate=func.now())
