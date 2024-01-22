from configuration.database_configuration import Base
from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    Integer,
    String,
    func,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship, backref
from models.lsd_model import LSD
from models.validator_model import Validator


class FeeRecipientMonitoring(Base):
    __tablename__ = "fee_recipient_monitoring"
 
    slot = Column(BigInteger, primary_key=True, nullable=False, index=True)
    validator_id = Column(
        String(100), ForeignKey(Validator.id), nullable=False, index=True
    )
    lsd_id = Column(String(50), ForeignKey(LSD.id), nullable=False, index=True)
    fee_recipient = Column(String(255), nullable=False, index=True)
    contains_fee_transaction = Column(Boolean, nullable=False, default=False)
    fee_transaction_hash = Column(String(255), nullable=True, index=True)
    compliant = Column(Boolean, nullable=False, default=False)

    created_datetime = Column(DateTime, default=func.now())
    updated_datetime = Column(DateTime, default=func.now(), onupdate=func.now())
