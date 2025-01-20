from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
import uuid
from datetime import datetime

Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    account_type = Column(String(50))
    billing_address_city = Column(String(100))
    phone_office = Column(String(20))
    RUC_code = Column(String(20), unique=True, nullable=False)
    shipping_address_street = Column(String(255))
    deleted = Column(Boolean, default=False)

    # Relación con Contact
    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deleted = Column(Boolean, default=False)
    date_entered = Column(DateTime, default=datetime.utcnow)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(100))
    department = Column(String(100))
    birthdate = Column(DateTime)
    phone_mobile = Column(String(20))
    phone_work = Column(String(20))
    email1 = Column(String(100), nullable=False)
    primary_address_street = Column(String(255))

    # Relación con Account
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    account = relationship("Account", back_populates="contacts")
