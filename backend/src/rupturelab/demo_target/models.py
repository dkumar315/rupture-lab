from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    name: str
    unit_price_cents: int


class OrderCreate(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=100)
    product_id: str
    quantity: int = Field(ge=1, le=100)


class Order(BaseModel):
    id: str
    client_request_id: str
    product_id: str
    quantity: int
    total_cents: int


class OrderResult(BaseModel):
    order: Order
    replayed: bool


class DemoStats(BaseModel):
    total_orders: int
    unique_client_requests: int
    duplicate_logical_writes: int


class EchoResponse(BaseModel):
    method: str
    query: list[tuple[str, str]]
    trace_id: str | None
    body: dict[str, str] | None
