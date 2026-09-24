from .helpers import CustomerDTO, MenuItemDTO, OrderDTO, CustomerOrdersDTO
from .models import Customer, Order, MenuItem, Base

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, event, select, func, delete

import datetime



class DBManager:

    #region meta methods

    def __init__(self, db_path:str = "database.db"):

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        @event.listens_for(self.engine, "connect")
        def enable_sqlite_fks(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)

    def populate_sample(self):
         ...

    #endregion


    #region CUSTOMER
    def add_customer(self, name:str, color:str) -> int:
        with Session(self.engine) as session:

            customer = Customer(name=name, color=color)
            session.add(customer)
            session.commit()
            return customer.id

    def remove_customer(self, id: int) -> bool:
        with Session(self.engine) as session:

            customer = session.get(Customer, id)

            if customer is None: return False

            session.delete(customer)
            session.commit()
            return True

    def get_customer(self, id: int) -> CustomerDTO | None:
        with Session(self.engine) as session:
            customer = session.get(Customer, id)
            return CustomerDTO.from_orm(customer) if customer else None

    def get_all_customers(self) -> list[CustomerDTO]:
        with Session(self.engine) as session:
            stmt = select(Customer).order_by(Customer.name)
            return [CustomerDTO.from_orm(c) for c in session.scalars(stmt)]

    def update_customer(self, id:int, name:str=None, color:str=None):
        with Session(self.engine) as session:
            customer = session.get(Customer, id)

            if customer is not None:

                if name is not None: customer.name = name
                if color is not None: customer.color = color

                session.commit()
    #endregion

    #region ORDER
    def upsert_order(self, customer_id:int, menu_item_id:int, date:datetime.date, count:int) -> OrderDTO|None:
        with Session(self.engine) as session:
            if count < 0:
                raise ValueError("count must not be negative")

            order = session.scalars(    
                select(Order).where(    
                    Order.customer_id == customer_id,   
                    Order.menu_item_id == menu_item_id, 
                    Order.date == date, 
                )
            ).one_or_none()

            if count == 0:
                if order is not None:
                    session.delete(order)
                    session.commit()
                return None

            if order is None:
                order = Order(customer_id=customer_id, menu_item_id=menu_item_id,
                              date=date, count=count)
                session.add(order)
            else:
                order.count = count

            session.commit()
            return OrderDTO.from_orm(order)

    def orders_of_customer(self, customer_id:int) -> list[OrderDTO]:
        with Session(self.engine) as session:
            stmt = (
                select(Order.id, MenuItem.code, Order.count, Order.date)
                .join(MenuItem, MenuItem.id == Order.menu_item_id)
                .where(Order.customer_id == customer_id)
                .order_by(Order.date, MenuItem.code)
            )
            return [
                OrderDTO(id=order_id, menu_item_code=code, count=count, date=order_date)
                for order_id, code, count, order_date in session.execute(stmt)
            ]

    #endregion

    #region MENU ITEM
    def add_menu_item(self, code:str, name:str=None):
        with Session(self.engine) as session:
            item = MenuItem(code=code, name=name)
            session.add(item)
            session.commit()

    def remove_menu_item(self, id: int, delete_orders: bool = False) -> bool:
        with Session(self.engine) as session:

            item = session.get(MenuItem, id)

            if item is None: return False

            if delete_orders:
                session.execute(delete(Order).where(Order.menu_item_id == id))

            session.delete(item)
            session.commit()   # raises IntegrityError if the item still has orders
            return True

    def order_counts_by_menu_item(self) -> dict[int, int]:
        with Session(self.engine) as session:
            stmt = select(Order.menu_item_id, func.count(Order.id)).group_by(Order.menu_item_id)
            return {item_id: count for item_id, count in session.execute(stmt)}

    def update_menu_item(self, id:int, name:str|None=None):
        with Session(self.engine) as session:
            item = session.get(MenuItem, id)
        
            if item is not None:
                if name is not None: item.name = name
                session.commit()

    def get_all_menu_items(self) -> list[MenuItemDTO]:
        with Session(self.engine) as session:
            stmt = select(MenuItem).order_by(MenuItem.code)
            return [MenuItemDTO.from_orm(i) for i in session.scalars(stmt)]
    #endregion

    #region HELPERS
    def orders_on(self, date: datetime.date) -> list[CustomerOrdersDTO]:
        with Session(self.engine) as session:
            stmt = (
                select(
                    Customer.id, Customer.name, Customer.color,
                    Order.id, MenuItem.code, Order.count, Order.date,
                )
                .join(Order, Order.customer_id == Customer.id)
                .join(MenuItem, MenuItem.id == Order.menu_item_id)
                .where(Order.date == date)
                .order_by(Customer.name, Customer.id, MenuItem.code)
            )

            result: dict[int, CustomerOrdersDTO] = {}
            for cust_id, name, color, order_id, code, count, order_date in session.execute(stmt):
                if cust_id not in result:
                    result[cust_id] = CustomerOrdersDTO(
                        customer=CustomerDTO(id=cust_id, name=name, color=color),
                        orders=[],
                    )
                result[cust_id].orders.append(
                    OrderDTO(id=order_id, menu_item_code=code, count=count, date=order_date)
                )

            return list(result.values())

    def totals_on(self, date: datetime.date) -> list[tuple[str, int]]:
        with Session(self.engine) as session:
            stmt = (
                select(MenuItem.code, func.sum(Order.count).label("total"))
                .join(Order, Order.menu_item_id == MenuItem.id)
                .where(Order.date == date)
                .group_by(MenuItem.id, MenuItem.code)
                .order_by(MenuItem.code)
            )
            return [(code, total) for code, total in session.execute(stmt)]
    #endregion


if __name__ == "__main__":
    manager = DBManager(":memory:")

    manager.add_customer("Marek", "blue")
    manager.add_menu_item("PZ1", "Margherita")

    today = datetime.date.today()
    manager.upsert_order(1, 1, today, 2)   # insert
    manager.upsert_order(1, 1, today, 5)   # update

    print(manager.orders_on(today))
    print(manager.totals_on(today))

    manager.upsert_order(1, 1, today, 0)   # delete
    print(manager.orders_on(today))        # []