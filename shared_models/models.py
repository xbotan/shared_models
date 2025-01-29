from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Text, Enum, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from shared_models.database import Base  # Usa el Base definido en shared_models.database
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import text, event, DDL


class Account(Base, SerializerMixin):
    __tablename__ = "accounts"

    # Controlar la serialización
    serialize_rules = ('-contacts.account', '-odts.account')

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Almacena UUID como texto
    date_entered = Column(DateTime, default=datetime.utcnow)
    name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=True)
    billing_address_city = Column(String(100), nullable=True)
    phone_office = Column(String(50), nullable=True)
    RUC_code = Column(String(11), unique=True, nullable=False)
    shipping_address_street = Column(String(255), nullable=True)
    deleted = Column(Boolean, default=False)

    # Relación con Contact
    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    odts = relationship("ODT", back_populates="account", cascade="all, delete-orphan")


class Contact(Base, SerializerMixin):
    __tablename__ = "contacts"

    # Controlar la serialización
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

    # Relación con Account
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    account = relationship("Account", back_populates="contacts")
    odts = relationship("ODT", back_populates="contact", cascade="all, delete-orphan")


# ENUM para tipos de archivo
class FileType(PyEnum):
    COST_BUDGET = "cost_budget"
    PURCHASE_COMPLIANCE = "purchase_compliance"
    REFERENCE_IMAGE = "reference_image"


# Entidad unificada para archivos
class FileAttachment(Base, SerializerMixin):
    __tablename__ = "file_attachments"

    serialize_rules = ('-odt',)  # Excluye completamente la relación ODT

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)  # Tipo del archivo
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)  # Campo adicional opcional

    # Relación con ODT
    odt_id = Column(CHAR(36), ForeignKey("odts.id"), nullable=False)
    odt = relationship("ODT", back_populates="file_attachments")


class ODT(Base, SerializerMixin):
    __tablename__ = "odts"

    serialize_rules = (
        '-account.odts',  # Evita que Account serialice sus ODTs
        '-contact.odts',  # Evita que Contact serialice sus ODTs
        '-file_attachments.odt',  # Evita que FileAttachment serialice el ODT padre
        '-_cost_budget_docs',  # Excluye propiedades calculadas
        '-_purchase_compliance_docs',
        '-_reference_images'
    )

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    odt_number = Column(Integer, nullable=False, unique=True)  # Nuevo campo secuencial
    date_entered = Column(DateTime, default=datetime.utcnow)
    project_name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2))  # Precio con 2 decimales
    delivery_type = Column(String(50))  # Ej: pickup, point_delivery, etc.
    delivery_address = Column(String(255))
    delivery_contact = Column(String(100))  # Nombre de contacto
    delivery_phone = Column(String(20))
    delivery_date = Column(DateTime)
    delivery_obs = Column(Text)  # Observaciones largas
    deleted = Column(Boolean, default=False)

    # Claves foráneas
    account_id = Column(CHAR(36), ForeignKey("accounts.id"), nullable=False)
    contact_id = Column(CHAR(36), ForeignKey("contacts.id"), nullable=False)

    # Relaciones
    account = relationship("Account", back_populates="odts")
    contact = relationship("Contact", back_populates="odts")

    # Relación unificada de archivos
    file_attachments = relationship("FileAttachment", back_populates="odt", cascade="all, delete-orphan")

    def to_dict(self, include_relations=False, include_files=False):
        base_dict = super().to_dict(rules=(
            '-account',
            '-contact',
            '-file_attachments',
            '-_cost_budget_docs',
            '-_purchase_compliance_docs',
            '-_reference_images'
        ))

        # Campos básicos
        data = {
            **base_dict,
            "account_id": self.account_id,
            "contact_id": self.contact_id,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
        }

        # Incluir relaciones básicas si se solicita
        if include_relations:
            data.update({
                "account": self.account.to_dict(rules=('-contacts', '-odts')) if self.account else None,
                "contact": self.contact.to_dict(rules=('-account', '-odts')) if self.contact else None,
                "file_attachments": [f.to_dict(rules=('-odt',)) for f in self.file_attachments]
            })

        # Incluir archivos categorizados si se solicita
        if include_files:
            data["files"] = {
                "cost_budget_docs": [
                    f.to_dict(rules=('-odt',))
                    for f in self.file_attachments
                    if f.file_type == FileType.COST_BUDGET.value
                ],
                "purchase_compliance_docs": [
                    f.to_dict(rules=('-odt',))
                    for f in self.file_attachments
                    if f.file_type == FileType.PURCHASE_COMPLIANCE.value
                ],
                "reference_images": [
                    f.to_dict(rules=('-odt',))
                    for f in self.file_attachments
                    if f.file_type == FileType.REFERENCE_IMAGE.value
                ]
            }

        return data

    # Propiedades para acceder a archivos por tipo
    @property
    def _cost_budget_docs(self):
        return [f for f in self.file_attachments if f.file_type == FileType.COST_BUDGET]

    @property
    def _purchase_compliance_docs(self):
        return [f for f in self.file_attachments if f.file_type == FileType.PURCHASE_COMPLIANCE]

    @property
    def _reference_images(self):
        return [f for f in self.file_attachments if f.file_type == FileType.REFERENCE_IMAGE]

    @classmethod
    def generate_next_odt_number(cls, session):
        # Bloquear la tabla para evitar condiciones de carrera
        counter = session.query(ODTNumberCounter).with_for_update().first()
        counter.last_number += 1
        session.commit()
        return counter.last_number


class ODTNumberCounter(Base):
    __tablename__ = "odt_number_counter"
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_number = Column(Integer, default=0, nullable=False)
