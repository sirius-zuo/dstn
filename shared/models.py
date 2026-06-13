import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, Text, LargeBinary, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class SupplierStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    PENDING_REGISTRATION = "pending_registration"

class SupplierRecord(Base):
    __tablename__ = "supplier_records"

    business_number: Mapped[str] = mapped_column(String(15), primary_key=True)
    business_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[SupplierStatus] = mapped_column(Enum(SupplierStatus))
    data_sources: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")  # JSON list
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    credential_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    did_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

class PasskeyRecord(Base):
    __tablename__ = "passkey_records"

    credential_id: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    business_number: Mapped[str] = mapped_column(String(15), index=True)
    public_key_cose: Mapped[bytes] = mapped_column(LargeBinary)
    did_key: Mapped[str] = mapped_column(String(512), unique=True)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class EncryptedCredential(Base):
    __tablename__ = "encrypted_credentials"

    did_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    cred_ex_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
