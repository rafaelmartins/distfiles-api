from flask import url_for, Response


def test_health(test_client):
    response: Response = test_client.get(url_for('main.health'))
    assert response.status_code == 200
    assert response.data == b'OK'
