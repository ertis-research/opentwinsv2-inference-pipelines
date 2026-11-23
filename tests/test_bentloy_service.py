import asyncio

import httpx
import pytest

from src.services.bentloy_service import BentloyError, BentloyService


def _response(status, json_body=None):
    return httpx.Response(status, json=json_body, request=httpx.Request("POST", "http://b/list_models"))


def test_get_model_sends_page_1(mocker):
    post = mocker.patch(
        "httpx.AsyncClient.post",
        return_value=_response(200, {"discovered_models": [{"service_name": "m1"}]}),
    )
    model = asyncio.run(BentloyService("http://b").get_model("m1"))
    assert model == {"service_name": "m1"}
    assert post.call_args.kwargs["json"]["page"] == 1
    assert post.call_args.kwargs["json"]["query"] == "m1"


def test_get_model_400_raises_bentloy_error(mocker):
    mocker.patch(
        "httpx.AsyncClient.post",
        return_value=_response(400, {"error": "Bad Request", "detail": "page must be >= 1"}),
    )
    with pytest.raises(BentloyError, match="page must be >= 1"):
        asyncio.run(BentloyService("http://b").get_model("m1"))
