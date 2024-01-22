from configuration.database_configuration import Base
from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    String,
    func,
)


class BlockMonitored(Base):
    __tablename__ = "blocks_monitored"
 
    slot = Column(BigInteger, primary_key=True, nullable=False, index=True)
    fee_recipient = Column(String(255), nullable=False, index=True)
    validator_index = Column(BigInteger, nullable=False, index=True)
    validator_id = Column(String(100), nullable=False, index=True)
    execution_chain_timestamp = Column(BigInteger, nullable=False, index=True)
    execution_chain_block_hash = Column(String(100), nullable=False, index=True)
    execution_chain_block_number = Column(BigInteger, nullable=False, index=True)
    execution_chain_gas_used = Column(BigInteger, nullable=False, index=True)

    created_datetime = Column(DateTime, default=func.now())
    updated_datetime = Column(DateTime, default=func.now(), onupdate=func.now())
