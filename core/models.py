# Sale, Product, Discount, Idea

from datetime import datetime, date

from sqlalchemy import (
    String, Float, Integer, Date, DateTime, ForeignKey,
    Boolean, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Тип позиции в справочнике "Цены"
PRODUCT_TYPE = "product"   # обычный товар
FRAME_TYPE = "frame"       # рамка


class Product(Base):
    """Справочник товаров и рамок (вкладка 'Цены')."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    type: Mapped[str] = mapped_column(String(20), default=PRODUCT_TYPE)  # product / frame
    price: Mapped[float] = mapped_column(Float, default=0.0)         # цена без скидки
    cost: Mapped[float] = mapped_column(Float, default=0.0)          # себестоимость
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # когда поступит в продажу
    note: Mapped[str] = mapped_column(Text, default="")

    def __repr__(self) -> str:
        return f"<Product {self.name} ({self.type})>"


class Discount(Base):
    """Справочник скидок (вкладка 'Скидки')."""
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class Sale(Base):
    """Продажа."""
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)

    sale_date: Mapped[date] = mapped_column(Date)                     # можно менять вручную
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    buyer_link: Mapped[str] = mapped_column(String(300), default="")  # ссылка на профиль
    buyer_name: Mapped[str] = mapped_column(String(200), default="")

    discount_id: Mapped[int | None] = mapped_column(
        ForeignKey("discounts.id"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    frame_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )

    amount_received: Mapped[float] = mapped_column(Float, default=0.0)  # сколько получил от покупателя
    profit: Mapped[float] = mapped_column(Float, default=0.0)           # считается автоматически

    dialog_link: Mapped[str] = mapped_column(String(300), default="")
    receipt_path: Mapped[str] = mapped_column(String(500), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    has_review: Mapped[bool] = mapped_column(Boolean, default=False)

    discount = relationship("Discount")
    product = relationship("Product", foreign_keys=[product_id])
    frame = relationship("Product", foreign_keys=[frame_id])


class Idea(Base):
    """Идеи (вкладка 'Идеи')."""
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)