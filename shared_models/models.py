from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Text, Enum, Integer, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship, foreign, remote, session as object_session
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from shared_models.database import Base  # Usa el Base definido en shared_models.database
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import and_  # Importa `and_` para filtrar relaciones en SQLAlchemy


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generar UUID si no se proporciona
        if not self.id:
            self.id = str(uuid.uuid4())

    @property
    def file_attachments(self):
        return object_session(self).query(FileAttachment).filter(
            FileAttachment.parent_type == ParentType.ACCOUNT.value,
            FileAttachment.parent_id == self.id
        ).all()


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generar UUID si no se proporciona
        if not self.id:
            self.id = str(uuid.uuid4())

    @property
    def file_attachments(self):
        return object_session(self).query(FileAttachment).filter(
            FileAttachment.parent_type == ParentType.CONTACT.value,
            FileAttachment.parent_id == self.id
        ).all()


# ENUM para tipos de archivo
class FileType(PyEnum):
    COST_BUDGET = "cost_budget"
    PURCHASE_COMPLIANCE = "purchase_compliance"
    REFERENCE_IMAGE = "reference_image"
# ENUM para tipos de entidades relacionadas


class ParentType(PyEnum):
    ODT = "odt"
    ACCOUNT = "account"
    CONTACT = "contact"
    # Agrega más tipos según necesites


# Entidad unificada para archivos
def generic_relationship(parent_type, parent_id):
    def _generic_relationship(cls):
        # Crea una relación dinámica
        @declared_attr
        def _relationship(cls):
            return relationship(
                'FileAttachment',
                primaryjoin=and_(
                    parent_type == cls.__name__.lower(),
                    foreign(parent_id) == remote(cls.id)
                ),
                viewonly=True,
                overlaps="related_entity"
            )
        return _relationship
    return _generic_relationship


class FileAttachment(Base, SerializerMixin):
    __tablename__ = "file_attachments"
    __table_args__ = (
        Index('ix_file_attachments_parent', 'parent_type', 'parent_id'),
    )

    serialize_rules = ('-related_entity.file_attachments',)  # Evitar recursión

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)  # Tipo del archivo
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)  # Campo adicional opcional

    parent_type = Column(Enum(ParentType), nullable=False)  # Tipo de entidad relacionada
    parent_id = Column(String(36), nullable=False)  # ID de la entidad relacionada

    # Relación dinámica (opcional, para acceso rápido)
    related_entity = generic_relationship("parent_type", "parent_id")


class ODT(Base, SerializerMixin):
    __tablename__ = "odts"

    __table_args__ = (
        Index('ix_odts_account_id', 'account_id'),
        Index('ix_odts_contact_id', 'contact_id'),
        Index('ix_odts_deleted', 'deleted'),
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generar UUID si no se proporciona
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self, include_relations=False, include_files=False):
        base_data = super().to_dict(rules=(
            '-account.odts',
            '-contact.odts',
            '-file_attachments.related_entity'
        ))

        data = {
            **base_data,
            "odt_number": self.odt_number,
            "date_entered": self.date_entered.isoformat() if self.date_entered else None,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "account_name": self.account.name if self.account else None,
            "contact_name": f"{self.contact.first_name} {self.contact.last_name}" if self.contact else None
        }

        if include_files:
            data["files"] = {
                "cost_budget": len(self._cost_budget_docs),
                "purchase_compliance": len(self._purchase_compliance_docs),
                "reference_images": len(self._reference_images)
            }

        return data

    @property
    def file_attachments(self):
        return object_session(self).query(FileAttachment).filter(
            FileAttachment.parent_type == ParentType.ODT.value,
            FileAttachment.parent_id == self.id
        ).all()

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
