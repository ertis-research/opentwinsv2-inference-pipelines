import asyncio

import httpx
import pytest

from src.services.bentloy_service import BentloyError, BentloyService


def _response(status, json_body=None):
    return httpx.Response(status, json=json_body, request=httpx.Request("POST", "http://b/list_models"))


def _model(name):
    return {
        "service_name": f"bentloy-model-{name}",
        "inferred_model_name": name,
        "predict_endpoint": f"http://bentloy-model-{name}:3000/predict",
    }


def _page(models, has_next=False, discovery=None):
    return {
        "discovered_models": models,
        "discovery": discovery or {"source": "k8s", "status": "ok", "error": None},
        "pagination": {"discovered_models": {"has_next": has_next}},
    }


def _get(mocker, *responses):
    post = mocker.patch("httpx.AsyncClient.post", side_effect=list(responses))
    return post


def _run(name="m1"):
    return asyncio.run(BentloyService("http://b").get_model(name))


def test_first_request_params(mocker):
    post = _get(mocker, _response(200, _page([_model("m1")])))
    assert _run("m1")["inferred_model_name"] == "m1"
    sent = post.call_args.kwargs["json"]
    assert sent == {"page": 1, "page_size": 100, "query": "m1"}


def test_exact_match_among_substring_matches(mocker):
    _get(mocker, _response(200, _page([_model("churn_v2_eu"), _model("churn_v2")])))
    assert _run("churn_v2")["inferred_model_name"] == "churn_v2"


def test_no_exact_match_returns_none(mocker):
    _get(mocker, _response(200, _page([_model("churn_v2_eu")])))
    assert _run("churn_v2") is None


def test_walks_pages(mocker):
    post = _get(
        mocker,
        _response(200, _page([_model("m1_eu")], has_next=True)),
        _response(200, _page([_model("m1")], has_next=False)),
    )
    assert _run("m1")["inferred_model_name"] == "m1"
    assert post.call_count == 2
    assert [c.kwargs["json"]["page"] for c in post.call_args_list] == [1, 2]


def test_stops_when_no_next_page(mocker):
    post = _get(mocker, _response(200, _page([_model("other")], has_next=False)))
    assert _run("m1") is None
    assert post.call_count == 1


def test_discovery_error_raises(mocker):
    _get(mocker, _response(200, _page([], discovery={"source": "k8s", "status": "error", "error": "k8s down"})))
    with pytest.raises(BentloyError, match="Bentloy model discovery failed: k8s down"):
        _run("m1")


def test_get_model_400_raises_bentloy_error(mocker):
    _get(mocker, _response(400, {"error": "Bad Request", "detail": "page must be >= 1"}))
    with pytest.raises(BentloyError, match="page must be >= 1"):
        _run("m1")


def test_infere_payload_uses_inferred_name_and_predict_endpoint(mocker):
    model = _model("m1")

    def fake_post(url, json=None, **kwargs):
        if url.endswith("/list_models"):
            return _response(200, _page([model]))
        return _response(200, {"predictions": [1]})

    post = mocker.patch("httpx.AsyncClient.post", side_effect=fake_post)
    result = asyncio.run(BentloyService("http://b").infere_with_model("m1", {"x": 1}))
    assert result == [1]
    predict = [c for c in post.call_args_list if c.args[0].endswith("/predict")][0]
    assert predict.kwargs["json"] == {
        "model_name": "m1",
        "model_url": model["predict_endpoint"],
        "data": {"x": 1},
    }
