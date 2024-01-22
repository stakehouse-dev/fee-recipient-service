from configuration.database_configuration import ETL_Base as Base
from sqlalchemy import Column, DateTime, BigInteger, Integer, String, func, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship, backref


class ValidatorLSD(Base):
    __tablename__ = "Validator_Indexes"

    bls_key = Column(String(255), primary_key=True, nullable=False, index=True)
    epoch = Column(DECIMAL(10, 0), primary_key=True, nullable=False, index=True)
    indexes = Column(DECIMAL(10, 0), nullable=False, index=True)
