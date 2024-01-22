from configuration.database_configuration import Base
from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    Boolean,
    func,
)
import atexit


class BackfillJobs(Base):
    __tablename__ = "manual_backfill_jobs"
 
    id = Column(BigInteger, primary_key=True, nullable=False, index=True, autoincrement=True)
    start_slot = Column(BigInteger, nullable=False, index=True)
    end_slot = Column(BigInteger, nullable=False, index=True)
    completed = Column(Boolean, nullable=False, index=True, default=False)
    stopped = Column(Boolean, nullable=False, index=True, default=False)

    created_datetime = Column(DateTime, default=func.now())
    updated_datetime = Column(DateTime, default=func.now(), onupdate=func.now())


    
