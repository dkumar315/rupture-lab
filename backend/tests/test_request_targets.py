import pytest

from rupturelab.request_targets import local_request_path


@pytest.mark.parametrize(
    "target",
    [
        "",
        f"/{'a' * 2048}",
        "demo/products",
        "//example.com/products",
        "/demo/products#fragment",
        "/demo\\products",
        "/demo/%ZZ",
        "/demo/%FF",
        "/%2F%2Fexample.com/products",
        "/demo/%5Cproducts",
        "/demo/%3Fsegment",
        "/demo/%23fragment",
        "/demo/%00products",
        "/demo/./products",
        "/demo/../products",
        "/demo/%2E%2E/products",
        "/_rupturelab",
        "/%5Frupturelab/fault",
    ],
)
def test_invalid_local_request_targets_are_rejected(target: str) -> None:
    with pytest.raises(ValueError):
        local_request_path(target)


def test_local_request_target_preserves_query_outside_normalized_path() -> None:
    assert local_request_path("/demo/%70roducts?tag=one&tag=two") == "/demo/products"
