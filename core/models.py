# Sale, Product, Discount, Idea

from datetime import datetime, date

from sqlalchemy import (
    String, Float, Integer, Date, DateTime, ForeignKey,
    Boolean, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.config import EXPENSE_FIXED


class Base(DeclarativeBase):
    pass


PRODUCT_TYPE = "product"
FRAME_TYPE = "frame"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    type: Mapped[str] = mapped_column(String(20), default=PRODUCT_TYPE)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class Expense(Base):
    """Справочник расходов (вкладка 'Расходы')."""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(20), default=EXPENSE_FIXED)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)

    sale_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    buyer_link: Mapped[str] = mapped_column(String(300), default="")
    buyer_name: Mapped[str] = mapped_column(String(200), default="")

    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    frame_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)

    size: Mapped[str] = mapped_column(String(50), default="")
    frame_size: Mapped[str] = mapped_column(String(50), default="")

    amount_received: Mapped[float] = mapped_column(Float, default=0.0)
    profit: Mapped[float] = mapped_column(Float, default=0.0)
    profit_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    dialog_link: Mapped[str] = mapped_column(String(300), default="")
    receipt_path: Mapped[str] = mapped_column(String(500), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    has_review: Mapped[bool] = mapped_column(Boolean, default=False)

    discount = relationship("Discount")
    product = relationship("Product", foreign_keys=[product_id])
    frame = relationship("Product", foreign_keys=[frame_id])
    expense_links = relationship(
        "SaleExpense", back_populates="sale", cascade="all, delete-orphan"
    )


class SaleExpense(Base):
    """Снимок применённого расхода к конкретной продаже (вариант А)."""
    __tablename__ = "sale_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"))
    expense_id: Mapped[int | None] = mapped_column(ForeignKey("expenses.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(200), default="")
    kind: Mapped[str] = mapped_column(String(20), default=EXPENSE_FIXED)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)

    sale = relationship("Sale", back_populates="expense_links")


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)