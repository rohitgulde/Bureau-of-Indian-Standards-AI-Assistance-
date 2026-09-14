"""
app/models/db_models.py
────────────────────────
SQLAlchemy ORM models for the BIS portal backend.

Tables
------
laboratories
    BIS-recognised / NABL-accredited testing laboratories.
    Used by the Lab Finder feature.

certification_schemes
    BIS certification pathways (ISI Mark, CRS, FMCS, Hallmarking, etc.)
    with target audience, mandatory/voluntary status, and portal URLs.

consumer_faqs
    Curated FAQs for consumers covering HUID verification, BIS Care App,
    complaints, and general IS-standard queries.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.database.session import Base

# ---------------------------------------------------------------------------
# HUID Record
# ---------------------------------------------------------------------------

class HuidRecord(Base):
    """
    Represents a Gold Hallmark HUID verification record.
    """
    __tablename__ = "huid_records"

    huid = Column(String(6), primary_key=True, index=True)
    jeweller_name = Column(String(255), nullable=False)
    jeweller_reg_no = Column(String(50), nullable=False)
    ahc_name = Column(String(255), nullable=False)
    ahc_location = Column(String(255), nullable=False)
    article_type = Column(String(100), nullable=False)
    purity_karat = Column(String(10), nullable=False)
    purity_fineness = Column(String(10), nullable=False)
    hallmarking_date = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False, default="Active")

    def to_dict(self) -> dict:
        return {
            "huid": self.huid,
            "jeweller_name": self.jeweller_name,
            "jeweller_reg_no": self.jeweller_reg_no,
            "ahc_name": self.ahc_name,
            "ahc_location": self.ahc_location,
            "article_type": self.article_type,
            "purity_karat": self.purity_karat,
            "purity_fineness": self.purity_fineness,
            "hallmarking_date": self.hallmarking_date.isoformat() if self.hallmarking_date else None,
            "status": self.status,
        }

# ---------------------------------------------------------------------------
# Laboratory
# ---------------------------------------------------------------------------

class Laboratory(Base):
    """
    Represents a BIS-recognised or NABL-accredited testing laboratory.

    Columns
    -------
    id               : auto-increment primary key
    name             : official lab name  (unique)
    state            : Indian state / UT
    city             : city
    pincode          : 6-digit PIN code
    address          : full postal address
    contact_email    : official contact e-mail
    phone            : phone number (may contain country code / extensions)
    accreditations   : pipe-separated list  e.g. "NABL | BIS Recognised"
    testing_scope    : comma-separated product / commodity categories
                       e.g. "Packaged Drinking Water, Cement, Steel"
    is_active        : soft-delete flag (False = delisted lab)
    latitude         : decimal latitude  (optional, for map display)
    longitude        : decimal longitude (optional, for map display)
    website          : lab website URL   (optional)
    created_at       : record creation timestamp (UTC)
    updated_at       : last modification timestamp (UTC)
    """

    __tablename__ = "laboratories"

    # --- Primary key -------------------------------------------------------
    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # --- Identity ----------------------------------------------------------
    name: str = Column(String(255), nullable=False, unique=True, index=True)

    # --- Location ----------------------------------------------------------
    state: str   = Column(String(100), nullable=False, index=True)
    city: str    = Column(String(100), nullable=False, index=True)
    pincode: str = Column(String(6),   nullable=False)
    address: str = Column(Text,        nullable=False)

    # --- Contact -----------------------------------------------------------
    contact_email: str = Column(String(255), nullable=True)
    phone: str         = Column(String(50),  nullable=True)
    website: str       = Column(String(512), nullable=True)

    # --- Accreditation & scope --------------------------------------------
    accreditations: str = Column(
        String(512),
        nullable=False,
        default="BIS Recognised",
        comment="Pipe-separated list: e.g. 'NABL | BIS Recognised | ISO 17025'",
    )
    testing_scope: str = Column(
        Text,
        nullable=False,
        comment="Comma-separated product categories tested by this lab",
    )

    # --- Geo ---------------------------------------------------------------
    latitude: float  = Column(String(20), nullable=True)
    longitude: float = Column(String(20), nullable=True)

    # --- Flags / audit -----------------------------------------------------
    is_active: bool = Column(Boolean, nullable=False, default=True, index=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --- Composite indices for Lab Finder queries --------------------------
    __table_args__ = (
        Index("ix_lab_city_active",    "city",  "is_active"),
        Index("ix_lab_state_active",   "state", "is_active"),
        Index("ix_lab_pincode_active", "pincode", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<Laboratory id={self.id!r} name={self.name!r} "
            f"city={self.city!r} active={self.is_active}>"
        )

    def to_dict(self) -> dict:
        """Serialise to a plain dict (used by FastAPI response models)."""
        return {
            "id":              self.id,
            "name":            self.name,
            "state":           self.state,
            "city":            self.city,
            "pincode":         self.pincode,
            "address":         self.address,
            "contact_email":   self.contact_email,
            "phone":           self.phone,
            "website":         self.website,
            "accreditations":  self.accreditations,
            "testing_scope":   self.testing_scope,
            "latitude":        self.latitude,
            "longitude":       self.longitude,
            "is_active":       self.is_active,
        }


# ---------------------------------------------------------------------------
# CertificationScheme
# ---------------------------------------------------------------------------

class CertificationScheme(Base):
    """
    A BIS certification pathway available to manufacturers, importers,
    or jewellers.

    Columns
    -------
    id                      : auto-increment primary key
    scheme_name             : official scheme name
                              e.g. "ISI Mark – Scheme I", "CRS – Scheme II"
    scheme_code             : short code  e.g. "ISI-I", "CRS-II", "FMCS", "HM"
    target_audience         : comma-separated audience roles
                              e.g. "Domestic Manufacturer, Importer"
    mandatory_or_voluntary  : "Mandatory" | "Voluntary"
    governing_regulation    : Act / regulation behind the scheme
                              e.g. "BIS Act 2016 – Section 16"
    applicable_products     : example product categories covered
    application_portal_url  : URL to apply online
                              e.g. "https://manakonline.in"
    standard_turnaround_time: indicative processing time  e.g. "60–90 working days"
    fee_structure_note      : brief note on fee basis  (optional)
    validity_period         : licence validity  e.g. "1 year (renewable)"
    description             : detailed operational guidelines / notes
    is_active               : soft-delete / deprecation flag
    created_at / updated_at : UTC audit timestamps
    """

    __tablename__ = "certification_schemes"

    # --- Primary key -------------------------------------------------------
    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # --- Identity ----------------------------------------------------------
    scheme_name: str = Column(String(255), nullable=False, unique=True, index=True)
    scheme_code: str = Column(String(20),  nullable=False, unique=True, index=True)

    # --- Audience & legal --------------------------------------------------
    target_audience: str = Column(
        String(512),
        nullable=False,
        comment="Comma-separated: 'Domestic Manufacturer', 'Importer', 'Jeweller'",
    )
    mandatory_or_voluntary: str = Column(
        String(20),
        nullable=False,
        default="Mandatory",
        comment="'Mandatory' or 'Voluntary'",
    )
    governing_regulation: str = Column(String(512), nullable=True)

    # --- Scope & portal ----------------------------------------------------
    applicable_products: str = Column(
        Text,
        nullable=True,
        comment="Representative product categories covered by this scheme",
    )
    application_portal_url: str = Column(
        String(512),
        nullable=True,
        default="https://manakonline.in",
        comment="URL for online application (Manak Online or scheme-specific portal)",
    )

    # --- Process metadata -------------------------------------------------
    standard_turnaround_time: str = Column(
        String(100),
        nullable=True,
        comment="Indicative end-to-end processing time",
    )
    fee_structure_note: str = Column(String(512), nullable=True)
    validity_period: str     = Column(String(100), nullable=True)

    # --- Rich content ------------------------------------------------------
    description: str = Column(
        Text,
        nullable=True,
        comment="Full operational guidelines, eligibility, and step-by-step process",
    )

    # --- Flags / audit -----------------------------------------------------
    is_active: bool = Column(Boolean, nullable=False, default=True, index=True)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_scheme_audience",   "target_audience"),
        Index("ix_scheme_mandatory",  "mandatory_or_voluntary", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<CertificationScheme id={self.id!r} code={self.scheme_code!r} "
            f"name={self.scheme_name!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":                       self.id,
            "scheme_name":              self.scheme_name,
            "scheme_code":              self.scheme_code,
            "target_audience":          self.target_audience,
            "mandatory_or_voluntary":   self.mandatory_or_voluntary,
            "governing_regulation":     self.governing_regulation,
            "applicable_products":      self.applicable_products,
            "application_portal_url":   self.application_portal_url,
            "standard_turnaround_time": self.standard_turnaround_time,
            "fee_structure_note":       self.fee_structure_note,
            "validity_period":          self.validity_period,
            "description":              self.description,
            "is_active":                self.is_active,
        }


# ---------------------------------------------------------------------------
# ConsumerFAQ
# ---------------------------------------------------------------------------

class ConsumerFAQ(Base):
    """
    A consumer-facing FAQ entry covering BIS processes, verification,
    complaints, and general IS-standard guidance.

    Columns
    -------
    id               : auto-increment primary key
    topic            : short FAQ title  e.g. "HUID Verification"
    category         : grouping label  e.g. "Hallmarking", "ISI Mark",
                       "Complaints", "General"
    keywords         : comma-separated search terms for fuzzy matching
    question         : the question as a consumer would phrase it
    resolution_steps : numbered, markdown-formatted step-by-step resolution
    related_url      : official BIS / GOI page for further reading (optional)
    related_scheme   : FK-like reference to a CertificationScheme code (optional)
    is_published     : False = draft; True = visible to end users
    sort_order       : display ordering within a category (lower = first)
    created_at / updated_at : UTC audit timestamps
    """

    __tablename__ = "consumer_faqs"

    # --- Primary key -------------------------------------------------------
    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # --- Content -----------------------------------------------------------
    topic: str    = Column(String(255), nullable=False, index=True)
    category: str = Column(String(100), nullable=False, index=True,
                           default="General")
    keywords: str = Column(
        Text,
        nullable=True,
        comment="Comma-separated keywords for full-text / semantic search",
    )
    question: str = Column(Text, nullable=False)
    resolution_steps: str = Column(
        Text,
        nullable=False,
        comment="Markdown-formatted numbered steps answering the question",
    )

    # --- References --------------------------------------------------------
    related_url: str    = Column(String(512), nullable=True)
    related_scheme: str = Column(
        String(20),
        nullable=True,
        comment="Matches CertificationScheme.scheme_code for cross-linking",
    )

    # --- Display -----------------------------------------------------------
    is_published: bool = Column(Boolean, nullable=False, default=True, index=True)
    sort_order: int    = Column(Integer,  nullable=False, default=0)

    # --- Audit -------------------------------------------------------------
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_faq_category_published", "category", "is_published"),
        Index("ix_faq_sort",               "sort_order"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsumerFAQ id={self.id!r} topic={self.topic!r} "
            f"category={self.category!r}>"
        )

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "topic":            self.topic,
            "category":         self.category,
            "keywords":         self.keywords,
            "question":         self.question,
            "resolution_steps": self.resolution_steps,
            "related_url":      self.related_url,
            "related_scheme":   self.related_scheme,
            "is_published":     self.is_published,
            "sort_order":       self.sort_order,
        }


# ---------------------------------------------------------------------------
# RAG / Knowledge Architecture Models
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"
    
    product_id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    product_name: str = Column(String(200), nullable=False, index=True)

    standards = relationship("ProductStandard", back_populates="product")


class Standard(Base):
    __tablename__ = "standards"
    
    standard_id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    is_number: str = Column(String(100), nullable=False, unique=True, index=True)
    title: str = Column(Text, nullable=True)

    products = relationship("ProductStandard", back_populates="standard")
    chunks = relationship("KnowledgeChunk", back_populates="standard", cascade="all, delete-orphan")


class ProductStandard(Base):
    __tablename__ = "product_standard"
    
    product_id: int = Column(Integer, ForeignKey("products.product_id"), primary_key=True)
    standard_id: int = Column(Integer, ForeignKey("standards.standard_id"), primary_key=True)
    relationship_type: str = Column(String(100), default="Product Standard")

    product = relationship("Product", back_populates="standards")
    standard = relationship("Standard", back_populates="products")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    chunk_id: str = Column(String(100), primary_key=True, comment="UUID matching Qdrant payload ID")
    standard_id: int = Column(Integer, ForeignKey("standards.standard_id"), index=True)
    page_number: int = Column(Integer, nullable=True)
    clause_number: str = Column(String(100), nullable=True)
    text: str = Column(Text, nullable=False)

    standard = relationship("Standard", back_populates="chunks")