import requests


def test_init_campaign_check_status_code_200():
    response = requests.get("http://127.0.0.1:8000/init?budget=10000&start=2020-09-10&end=2020-09-30&cpid=1")
    assert response.status_code == 200


def test_init_campaign_check_status_code_500():
    response = requests.get("http://127.0.0.1:8000/init?budget=10000&start=2020-09-10&end=2020-09-30&cpid=1")
    assert response.status_code == 500


def test_status_output_is_json():
    response = requests.get("http://127.0.0.1:8000/campaign/1/status")
    assert response.headers["Content-Type"] == "application/json"


def test_status_for_a_single_tz():
    response = requests.get("http://127.0.0.1:8000/campaign/1/status/America--New_York")
    response_body = response.json()
    assert response_body["spent"] == 0


def test_post_br():
    response = requests.post("http://127.0.0.1:8000/br?tz=America%2FNew_York&brid=1&imps=1&cpm=1000&cpid=1")
    response_body = response.json()
    assert response_body["buying"]


def test_send_win_notif():
    response = requests.get("http://127.0.0.1:8000/notif?cpid=1&status=win&brid=1")
    assert response.status_code == 200


def test_status_has_changed():
    response = requests.get("http://127.0.0.1:8000/campaign/1/status/America--New_York")
    response_body = response.json()
    assert response_body["spent"] == 1
