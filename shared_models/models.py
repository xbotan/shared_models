from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Text, Enum, Integer, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship, foreign, remote
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from shared_models.database import Base
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.sql import and_


class Account(Base, SerializerMixin):
    __tablename__ = "accounts"
    serialize_rules = ('-contacts.account', '-odts.account')

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date_entered = Column(DateTime, default=datetime.utcnow)
    name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=True)
    billing_address_city = Column(String(100), nullable=True)
    phone_office = Column(String(50), nullable=True)
    RUC_code = Column(String(11), unique=True, nullable=False)
    shipping_address_street = Column(String(255), nullable=True)
    deleted = Column(Boolean, default=False)

    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    odts = relationship("ODT", back_populates="account", cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())


class Contact(Base, SerializerMixin):
    __tablename__ = "contacts"
    serialize_rules = ('-account.contacts', '-odts.contacts')

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

    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    account = relationship("Account", back_populates="contacts")
    odts = relationship("ODT", back_populates="contact", cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())


class FileType(PyEnum):
    COST_BUDGET = "cost_budget"
    PURCHASE_COMPLIANCE = "purchase_compliance"
    REFERENCE_IMAGE = "reference_image"


class ParentType(PyEnum):
    ODT = "odt"
    ACCOUNT = "account"
    CONTACT = "contact"


class FileAttachment(Base, SerializerMixin):
    __tablename__ = "file_attachments"
    __table_args__ = (
        Index('ix_file_attachments_parent', 'parent_type', 'parent_id'),
    )

    serialize_rules = ('-related_entity',)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    parent_type = Column(Enum(ParentType), nullable=False)
    parent_id = Column(String(36), nullable=False)

    # Relación directa con ODT
    odt = relationship(
        "ODT",
        primaryjoin=and_(
            parent_type == ParentType.ODT.value,
            foreign(parent_id) == remote(id)
        ),
        backref="file_attachments",
        overlaps="related_entity"
    )


class ODT(Base, SerializerMixin):
    __tablename__ = "odts"
    __table_args__ = (
        Index('ix_odts_account_id', 'account_id'),
        Index('ix_odts_contact_id', 'contact_id'),
        Index('ix_odts_deleted', 'deleted'),
    )

    serialize_rules = (
        '-account.odts',
        '-contact.odts',
        '-file_attachments.odt'
    )

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    odt_number = Column(Integer, nullable=False, unique=True)
    date_entered = Column(DateTime, default=datetime.utcnow)
    project_name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2))
    delivery_type = Column(String(50))
    delivery_address = Column(String(255))
    delivery_contact = Column(String(100))
    delivery_phone = Column(String(20))
    delivery_date = Column(DateTime)
    delivery_obs = Column(Text)
    deleted = Column(Boolean, default=False)

    account_id = Column(CHAR(36), ForeignKey("accounts.id"), nullable=False)
    contact_id = Column(CHAR(36), ForeignKey("contacts.id"), nullable=False)

    account = relationship("Account", back_populates="odts")
    contact = relationship("Contact", back_populates="odts")

    def to_dict(self, include_relations=False, include_files=False):
        base_data = super().to_dict(rules=(
            '-account.odts',
            '-contact.odts',
            '-file_attachments.odt'
        ))

        data = {
            **base_data,
            "odt_number": self.odt_number,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "account_name": self.account.name if self.account else None,
            "contact_name": f"{self.contact.first_name} {self.contact.last_name}" if self.contact else None
        }

        if include_files:
            data["files"] = [
                {
                    "file_path": f.file_path,
                    "file_type": f.file_type.value,
                    "description": f.description
                }
                for f in self.file_attachments
            ]

        return data

    @classmethod
    def generate_next_odt_number(cls, session):
        counter = session.query(ODTNumberCounter).with_for_update().first()
        counter.last_number += 1
        session.commit()
        return counter.last_number


class ODTNumberCounter(Base):
    __tablename__ = "odt_number_counter"
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_number = Column(Integer, default=0, nullable=False)
