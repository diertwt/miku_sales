# все функции работы с БД

from datetime import date, datetime

from sqlalchemy import select, func, extract
from sqlalchemy.orm import selectinload

from core.config import TAX_PERCENT, EXPENSE_FIXED, EXPENSE_PERCENT
from core.db import SessionLocal
from core.models import (
    Product, Discount, Sale, SaleExpense, Expense, Idea,
    PRODUCT_TYPE, FRAME_TYPE,
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
            name=name, price=price, cost=cost,
            start_date=start_date, note=note,
        )
        p.type = type_
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
            attr = "type" if k == "type_" else k
            setattr(p, attr, v)
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


# ---------- Расходы ----------

def list_expenses() -> list[Expense]:
    with SessionLocal() as s:
        return list(s.scalars(select(Expense).order_by(Expense.name)))


def add_expense(
    name: str,
    kind: str = EXPENSE_FIXED,
    value: float = 0.0,
    is_default: bool = False,
    note: str = "",
) -> Expense:
    with SessionLocal() as s:
        e = Expense(
            name=name, kind=kind, value=value,
            is_default=is_default, note=note,
        )
        s.add(e)
        s.commit()
        s.refresh(e)
        return e


def update_expense(expense_id: int, **fields) -> None:
    with SessionLocal() as s:
        e = s.get(Expense, expense_id)
        if not e:
            return
        for k, v in fields.items():
            setattr(e, k, v)
        s.commit()


def delete_expense(expense_id: int) -> None:
    with SessionLocal() as s:
        e = s.get(Expense, expense_id)
        if e:
            s.delete(e)
            s.commit()


# ---------- Расчёт прибыли ----------

def expense_amount(kind: str, value: float, base_amount: float) -> float:
    """Считает сумму расхода в рублях."""
    if kind == EXPENSE_PERCENT:
        return round(base_amount * value / 100.0, 2)
    return round(value, 2)


def calc_profit(
    amount_received: float,
    product_cost: float = 0.0,
    frame_cost: float = 0.0,
    expenses_total: float = 0.0,
) -> float:
    """
    Формула:
      сумма − налог% − себестоимость_товара − себестоимость_рамки − Σ расходов
    """
    tax = amount_received * TAX_PERCENT / 100.0
    return round(
        amount_received - tax - product_cost - frame_cost - expenses_total, 2
    )


# ---------- Продажи ----------

def add_sale(
    *,
    sale_date: date,
    buyer_link: str,
    buyer_name: str,
    amount_received: float,
    product_id: int | None = None,
    frame_id: int | None = None,
    discount_id: int | None = None,
    size: str = "",
    frame_size: str = "",
    dialog_link: str = "",
    receipt_path: str = "",
    note: str = "",
    has_review: bool | None = None,
    expenses: list[dict] | None = None,
    profit_override: float | None = None,
) -> Sale:
    with SessionLocal() as s:
        product = s.get(Product, product_id) if product_id else None
        frame = s.get(Product, frame_id) if frame_id else None

        product_cost = product.cost if product else 0.0
        frame_cost = frame.cost if frame else 0.0

        expenses = expenses or []
        total_expenses = 0.0
        snapshots: list[SaleExpense] = []
        for e in expenses:
            amt = expense_amount(e["kind"], e["value"], amount_received)
            total_expenses += amt
            snapshots.append(SaleExpense(
                expense_id=e.get("expense_id"),
                name=e["name"], kind=e["kind"],
                value=e["value"], amount=amt,
            ))

        auto_profit = calc_profit(
            amount_received, product_cost, frame_cost, total_expenses
        )
        final_profit = (
            profit_override if profit_override is not None else auto_profit
        )
        is_manual = profit_override is not None

        if has_review is None:
            has_review = _last_review_status(s, buyer_link)

        sale = Sale(
            sale_date=sale_date,
            buyer_link=buyer_link,
            buyer_name=buyer_name,
            amount_received=amount_received,
            profit=final_profit,
            profit_manual=is_manual,
            product_id=product_id,
            frame_id=frame_id,
            discount_id=discount_id,
            size=size,
            frame_size=frame_size,
            dialog_link=dialog_link,
            receipt_path=receipt_path,
            note=note,
            has_review=bool(has_review),
        )
        
        sale.expense_links = snapshots
        s.add(sale)
        s.commit()
        s.refresh(sale)
        return sale


def _last_review_status(session, buyer_link: str) -> bool:
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


def update_sale(
    sale_id: int,
    *,
    expenses: list[dict] | None = None,
    profit_override: float | None = None,
    **fields,
) -> None:
    with SessionLocal() as s:
        sale = s.get(Sale, sale_id)
        if not sale:
            return

        for k, v in fields.items():
            setattr(sale, k, v)

        if expenses is not None:
            sale.expense_links.clear()
            for e in expenses:
                amt = expense_amount(e["kind"], e["value"], sale.amount_received)
                sale.expense_links.append(SaleExpense(
                    expense_id=e.get("expense_id"),
                    name=e["name"], kind=e["kind"],
                    value=e["value"], amount=amt,
                ))

        product = s.get(Product, sale.product_id) if sale.product_id else None
        frame = s.get(Product, sale.frame_id) if sale.frame_id else None
        total_exp = sum(link.amount for link in sale.expense_links)
        auto = calc_profit(
            sale.amount_received,
            product.cost if product else 0.0,
            frame.cost if frame else 0.0,
            total_exp,
        )

        if profit_override is not None:
            sale.profit = profit_override
            sale.profit_manual = True
        else:
            sale.profit = auto
            sale.profit_manual = False

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
        stmt = (
            select(Sale)
            .options(
                selectinload(Sale.discount),
                selectinload(Sale.product),
                selectinload(Sale.frame),
                selectinload(Sale.expense_links),
            )
            .order_by(Sale.sale_date.desc(), Sale.id.desc())
        )
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
            select(Sale)
            .order_by(Sale.sale_date.desc(), Sale.id.desc())
            .limit(limit)
        )
        return list(s.scalars(stmt))


def sales_by_day(
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[tuple[date, float, float]]:
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


# ---------- Аналитика для графиков ----------

def top_products_by_month(
    year: int, month: int, product_type: str | None = None, limit: int = 10,
) -> list[tuple[str, int]]:
    """Топ товаров (или рамок) за месяц: [(название, количество продаж)]."""
    with SessionLocal() as s:
        stmt = (
            select(Product.name, func.count(Sale.id))
            .join(Sale, Sale.product_id == Product.id)
            .where(
                extract("year", Sale.sale_date) == year,
                extract("month", Sale.sale_date) == month,
            )
            .group_by(Product.name)
            .order_by(func.count(Sale.id).desc())
            .limit(limit)
        )
        if product_type:
            stmt = stmt.where(Product.type == product_type)
        return [(row[0], int(row[1])) for row in s.execute(stmt)]


def frames_by_month(year: int, month: int, limit: int = 10) -> list[tuple[str, int]]:
    """Какие рамки брали за месяц и сколько раз."""
    with SessionLocal() as s:
        stmt = (
            select(Product.name, func.count(Sale.id))
            .join(Sale, Sale.frame_id == Product.id)
            .where(
                extract("year", Sale.sale_date) == year,
                extract("month", Sale.sale_date) == month,
            )
            .group_by(Product.name)
            .order_by(func.count(Sale.id).desc())
            .limit(limit)
        )
        return [(row[0], int(row[1])) for row in s.execute(stmt)]