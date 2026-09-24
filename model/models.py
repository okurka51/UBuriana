import datetime

from sqlalchemy import String, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

class Base(DeclarativeBase):
    ...

class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    color: Mapped[str] = mapped_column(nullable=False)

    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    

class Order(Base):
    __tablename__ = "order"
    __table_args__ = (CheckConstraint("count > 0", name="ck_order_count_positive"),
                      UniqueConstraint("customer_id", "menu_item_id", "date", name="uq_order_customer_item_date"))

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_item.id"), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    count: Mapped[int] = mapped_column(nullable=False)

    menu_item: Mapped["MenuItem"] = relationship(back_populates="orders")
    customer:  Mapped["Customer"] = relationship(back_populates="orders")

    menu_item_code = association_proxy("menu_item", "code")

class MenuItem(Base):
    __tablename__ = "menu_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True )
    name: Mapped[str|None] = mapped_column(String(100))

    orders: Mapped[list["Order"]] = relationship(back_populates="menu_item")