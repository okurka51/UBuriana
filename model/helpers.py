from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Customer, MenuItem, Order


@dataclass(frozen=True)
class CustomerDTO:
    id: int
    name: str
    color: str

    @classmethod
    def from_orm(cls, customer: Customer) -> CustomerDTO:
        return cls(
            id=customer.id,
            name=customer.name,
            color=customer.color,
        )

@dataclass(frozen=True)
class OrderDTO:
    id: int
    menu_item_code: str
    count: int
    date: datetime.date

    @classmethod
    def from_orm(cls, order: Order) -> OrderDTO:
        return cls(
            id=order.id,
            menu_item_code=order.menu_item.code,
            count=order.count,
            date=order.date,
        )

@dataclass(frozen=True)
class MenuItemDTO:
    id: int
    code: str
    name: str | None

    @classmethod
    def from_orm(cls, item: MenuItem) -> MenuItemDTO:
        return cls(
            id=item.id,
            code=item.code,
            name=item.name,
        )

@dataclass(frozen=True)
class CustomerOrdersDTO:
    customer: CustomerDTO
    orders: list[OrderDTO]