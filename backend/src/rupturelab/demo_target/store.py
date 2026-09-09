from collections import Counter
from threading import Lock

from rupturelab.demo_target.models import DemoStats, Order, OrderCreate, Product


class DemoStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._products = {
            "keyboard": Product(
                id="keyboard",
                name="Mechanical Keyboard",
                unit_price_cents=12900,
            ),
            "mouse": Product(
                id="mouse",
                name="Wireless Mouse",
                unit_price_cents=6900,
            ),
        }
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._orders: dict[str, Order] = {}
            self._idempotency_keys: dict[str, str] = {}
            self._next_order_id = 1

    def list_products(self) -> list[Product]:
        return list(self._products.values())

    def list_orders(self) -> list[Order]:
        with self._lock:
            return list(self._orders.values())

    def create_order(
        self,
        request: OrderCreate,
        idempotency_key: str | None,
    ) -> tuple[Order, bool]:
        with self._lock:
            if idempotency_key is not None:
                existing_id = self._idempotency_keys.get(idempotency_key)
                if existing_id is not None:
                    return self._orders[existing_id], True

            product = self._products.get(request.product_id)
            if product is None:
                raise KeyError(request.product_id)

            order_id = f"ord-{self._next_order_id:04d}"
            self._next_order_id += 1

            order = Order(
                id=order_id,
                client_request_id=request.client_request_id,
                product_id=request.product_id,
                quantity=request.quantity,
                total_cents=product.unit_price_cents * request.quantity,
            )

            self._orders[order_id] = order

            if idempotency_key is not None:
                self._idempotency_keys[idempotency_key] = order_id

            return order, False

    def stats(self) -> DemoStats:
        with self._lock:
            request_counts = Counter(order.client_request_id for order in self._orders.values())

            duplicate_writes = sum(count - 1 for count in request_counts.values() if count > 1)

            return DemoStats(
                total_orders=len(self._orders),
                unique_client_requests=len(request_counts),
                duplicate_logical_writes=duplicate_writes,
            )


store = DemoStore()
