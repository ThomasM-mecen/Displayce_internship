import requests as req
import pytest
from datetime import datetime, timedelta


# Yield_fixture fait office de setup & teardown
@pytest.yield_fixture()
def init_campaign():
    # Setup se place avant le yield
    response = req.post("http://127.0.0.1:8000/campaign", json={"cpid": "1"})

    yield response
    # Teardown après le yield
    req.delete("http://127.0.0.1:8000/campaign", json={"cpid": "1"})


@pytest.yield_fixture()
def init_li():
    # Setup se place avant le yield
    req.post("http://127.0.0.1:8000/campaign", json={"cpid": "1"})
    date_start = datetime.now()
    date_end = date_start + timedelta(days=7)
    response = req.post("http://127.0.0.1:8000/campaign/1/init", json={
        "budget": 10000,
        "start": str(date_start.year) + "-" + str(date_start.month) + "-" + str(date_start.day),
        "end": str(date_end.year) + "-" + str(date_end.month) + "-" + str(date_end.day),
        "liid": "1"
    })

    yield response
    # Teardown après le yield
    req.delete("http://127.0.0.1:8000/campaign/1/init", json={
        "liid": "1"
    })
    req.delete("http://127.0.0.1:8000/campaign", json={"cpid": "1"})


def test_init_campaign_check_status_code(init_campaign):
    response1 = init_campaign
    response2 = req.post("http://127.0.0.1:8000/campaign", json={"cpid": "1"})
    assert response1.status_code == 200
    assert response2.status_code == 422


def test_init_li_check_status_code(init_li):
    response1 = init_li
    date_start = datetime.now()
    date_end = date_start + timedelta(days=7)
    response2 = req.post("http://127.0.0.1:8000/campaign/1/init", json={
        "budget": 10000,
        "start": str(date_start.year) + "-" + str(date_start.month) + "-" + str(date_start.day),
        "end": str(date_end.year) + "-" + str(date_end.month) + "-" + str(date_end.day),
        "liid": "1"
    })
    assert response1.status_code == 200
    assert response2.status_code == 422


def test_buying_br(init_li):
    response_br = req.post("http://127.0.0.1:8000/li/1/br", json={
        "tz": "America/New_York",
        "brid": 1,
        "imps": 1,
        "cpm": 333.333333333333333333333333333333333333333333333333333333
    })
    response_br_body = response_br.json()
    response_status_before_notif = req.get("http://127.0.0.1:8000/li/1/status")
    response_status_before_notif_body = response_status_before_notif.json()
    req.post("http://127.0.0.1:8000/li/1/notif", json={
        "status": "win",
        "brid": 1
    })
    response_status_after_notif = req.get("http://127.0.0.1:8000/li/1/status")
    response_status_after_notif_body = response_status_after_notif.json()
    print(response_br_body)
    assert response_br_body["buying"]
    assert response_status_before_notif_body["spent"] == 0
    assert pytest.approx(response_status_after_notif_body["spent"], 0.001) == 0.333
