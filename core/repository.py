# все функции работы с БД

from datetime import date, datetime
from typing import Iterable

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from core.config import TAX_PERCENT
from core.db import SessionLocal
from core.models import (
    Base, Product, Discount, Sale, Idea,
    PRODUCT_TYPE, FRAME_TYPE,
)


# ---------- Хелпер для eager-load связей у Sale ----------

def _sale_stmt():
    """SELECT по продажам сразу с подгрузкой связей (discount, product, frame)."""
    return select(Sale).options(
        selectinload(Sale.discount),
        selectinload(Sale.product),
        selectinload(Sale.frame),
    )


# ---------- Продукты / рамки ----------

def list_products(type_: str | None = None) -> list[Product]:
    with SessionLocal() as s:
        stmt = select(Product).order_by(Product.name)
        if type_:
            stmt = stmt.where(Product.type == type_)
        return list(s.scalars(stmt))


def add_product(
    name: str,
    type_: str = PRODUCT_TYPE,
    price: float = 0.0,
    cost: float = 0.0,
    start_date: date | None = None,
    note: str = "",
) -> Product:
    with SessionLocal() as s:
        p = Product(
            name=name,
            price=price,
            cost=cost,
            start_date=start_date,
            note=note,
        )
        p.type = type_           # ← ставим после создания
        s.add(p)
        s.commit()
        s.refresh(p)
        return p

def update_product(product_id: int, **fields) -> None:
    with SessionLocal() as s:
        p = s.get(Product, product_id)
        if not p:
            return
        for k, v in fields.items():
            setattr(p, k, v)
        s.commit()


def delete_product(product_id: int) -> None:
    with SessionLocal() as s:
        p = s.get(Product, product_id)
        if p:
            s.delete(p)
            s.commit()


# ---------- Скидки ----------

def list_discounts() -> list[Discount]:
    with SessionLocal() as s:
        return list(s.scalars(select(Discount).order_by(Discount.name)))


def add_discount(
    name: str,
    percent: float = 0.0,
    start_date: date | None = None,
    end_date: date | None = None,
    note: str = "",
) -> Discount:
    with SessionLocal() as s:
        d = Discount(
            name=name, percent=percent,
            start_date=start_date, end_date=end_date, note=note,
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        return d


def update_discount(discount_id: int, **fields) -> None:
    with SessionLocal() as s:
        d = s.get(Discount, discount_id)
        if not d:
            return
        for k, v in fields.items():
            setattr(d, k, v)
        s.commit()


def delete_discount(discount_id: int) -> None:
    with SessionLocal() as s:
        d = s.get(Discount, discount_id)
        if d:
            s.delete(d)
            s.commit()


# ---------- Продажи ----------

def calc_profit(
    amount_received: float,
    product_cost: float = 0.0,
    frame_cost: float = 0.0,
) -> float:
    """Формула: сумма − налог% − себестоимость товара − себестоимость рамки."""
    tax = amount_received * TAX_PERCENT / 100.0
    return round(amount_received - tax - product_cost - frame_cost, 2)


def add_sale(
    *,
    sale_date: date,
    buyer_link: str,
    buyer_name: str,
    amount_received: float,
    product_id: int | None = None,
    frame_id: int | None = None,
    discount_id: int | None = None,
    dialog_link: str = "",
    receipt_path: str = "",
    note: str = "",
    has_review: bool | None = None,
) -> Sale:
    """
    Создаёт продажу. Прибыль считается автоматически.
    Если has_review=None — берём последнее известное значение по buyer_link.
    """
    with SessionLocal() as s:
        product = s.get(Product, product_id) if product_id else None
        frame = s.get(Product, frame_id) if frame_id else None

        product_cost = product.cost if product else 0.0
        frame_cost = frame.cost if frame else 0.0

        profit = calc_profit(amount_received, product_cost, frame_cost)

        if has_review is None:
            has_review = _last_review_status(s, buyer_link)

        sale = Sale(
            sale_date=sale_date,
            buyer_link=buyer_link,
            buyer_name=buyer_name,
            amount_received=amount_received,
            profit=profit,
            product_id=product_id,
            frame_id=frame_id,
            discount_id=discount_id,
            dialog_link=dialog_link,
            receipt_path=receipt_path,
            note=note,
            has_review=bool(has_review),
        )
        s.add(sale)
        s.commit()

        # перечитываем с eager-load, чтобы возвращаемый объект был "полным"
        return s.scalar(_sale_stmt().where(Sale.id == sale.id))


def _last_review_status(session, buyer_link: str) -> bool:
    """Последний известный статус отзыва по этому покупателю."""
    if not buyer_link:
        return False
    stmt = (
        select(Sale.has_review)
        .where(Sale.buyer_link == buyer_link)
        .order_by(Sale.sale_date.desc(), Sale.id.desc())
        .limit(1)
    )
    val = session.scalar(stmt)
    return bool(val) if val is not None else False


def update_sale(sale_id: int, **fields) -> None:
    """Обновление полей продажи; при изменении суммы/товара/рамки — пересчёт прибыли."""
    with SessionLocal() as s:
        sale = s.get(Sale, sale_id)
        if not sale:
            return

        for k, v in fields.items():
            setattr(sale, k, v)

        # пересчёт прибыли, если затронули что-то из формулы
        recalc_keys = {"amount_received", "product_id", "frame_id"}
        if recalc_keys & fields.keys():
            product = s.get(Product, sale.product_id) if sale.product_id else None
            frame = s.get(Product, sale.frame_id) if sale.frame_id else None
            sale.profit = calc_profit(
                sale.amount_received,
                product.cost if product else 0.0,
                frame.cost if frame else 0.0,
            )
        s.commit()


def delete_sale(sale_id: int) -> None:
    with SessionLocal() as s:
        sale = s.get(Sale, sale_id)
        if sale:
            s.delete(sale)
            s.commit()


def list_sales(
    from_date: date | None = None,
    to_date: date | None = None,
    buyer_link: str | None = None,
) -> list[Sale]:
    with SessionLocal() as s:
        stmt = _sale_stmt().order_by(Sale.sale_date.desc(), Sale.id.desc())
        if from_date:
            stmt = stmt.where(Sale.sale_date >= from_date)
        if to_date:
            stmt = stmt.where(Sale.sale_date <= to_date)
        if buyer_link:
            stmt = stmt.where(Sale.buyer_link == buyer_link)
        return list(s.scalars(stmt))


def last_sales(limit: int = 5) -> list[Sale]:
    with SessionLocal() as s:
        stmt = (
            _sale_stmt()
            .order_by(Sale.sale_date.desc(), Sale.id.desc())
            .limit(limit)
        )
        return list(s.scalars(stmt))


def sales_by_day(
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[tuple[date, float, float]]:
    """
    Возвращает список (день, сумма_полученная, чистая_прибыль) по дням.
    """
    with SessionLocal() as s:
        stmt = select(
            Sale.sale_date.label("d"),
            func.sum(Sale.amount_received).label("amount"),
            func.sum(Sale.profit).label("profit"),
        ).group_by(Sale.sale_date).order_by(Sale.sale_date)
        if from_date:
            stmt = stmt.where(Sale.sale_date >= from_date)
        if to_date:
            stmt = stmt.where(Sale.sale_date <= to_date)
        return [(r.d, float(r.amount or 0), float(r.profit or 0)) for r in s.execute(stmt)]


def user_sales(buyer_link: str) -> list[Sale]:
    """Все покупки конкретного пользователя (для кнопки 'Проверка пользователя')."""
    return list_sales(buyer_link=buyer_link)


# ---------- Идеи ----------

def list_ideas() -> list[Idea]:
    with SessionLocal() as s:
        return list(s.scalars(select(Idea).order_by(Idea.created_at.desc())))


def add_idea(text: str) -> Idea:
    with SessionLocal() as s:
        idea = Idea(text=text)
        s.add(idea)
        s.commit()
        s.refresh(idea)
        return idea


def delete_idea(idea_id: int) -> None:
    with SessionLocal() as s:
        idea = s.get(Idea, idea_id)
        if idea:
            s.delete(idea)
            s.commit()