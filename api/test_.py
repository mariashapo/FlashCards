import os
from unittest.mock import MagicMock, patch

import pytest

from app import app as flask_app

# Supabase credentials
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def mock_openai_api():
    with patch("openai.Completion.create") as mock:
        mock.return_value = MagicMock(
            choices=[
                MagicMock(
                    text=str(
                        [
                            {"English": "Hello", "Spanish": "Hola"},
                            {"English": "Goodbye", "Spanish": "Adiós"},
                        ]
                    )
                )
            ]
        )
        yield mock


@pytest.fixture
def mock_supabase(mocker):
    mocked_select = MagicMock(
        return_value=MagicMock(
            execute=MagicMock(
                return_value=MagicMock(
                    data=[{"username": "gpo23", "password": "gpo23Passwort"}]
                )
            )
        )
    )
    mocked_insert = MagicMock(
        return_value=MagicMock(
            execute=MagicMock(
                return_value=MagicMock(
                    data=[{"id": 1, "username": "gpo23", "password": "gpo23Passwort"}]
                )
            )
        )
    )
    mocked_table = MagicMock(select=mocked_select, insert=mocked_insert)
    mocker.patch("app.supabase.table", return_value=mocked_table)
    return mocked_table


def test_login_route(client):
    response = client.post(
        "/login",
        data=dict(username="gpo23", password="gpo23Passwort"),
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_signup_route(client):
    response = client.post(
        "/signup",
        data=dict(username="newuser", password="newpassword"),
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200


def test_logout_route(client):
    client.post(
        "/login",
        data=dict(username="gpo23", password="gpo23Passwort"),
        follow_redirects=True,
    )
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200


def test_add_new_topic_route(client):
    client.post(
        "/login",
        data=dict(username="gpo23", password="gpo23Passwort"),
        follow_redirects=True,
    )
    response = client.post(
        "/add_new_topic", data={"topicName": "New Topic"}, follow_redirects=True
    )
    assert response.status_code == 200


def test_unauthorized_access(client):
    response = client.get("/topics")
    assert response.status_code == 302


def test_start_study_session(client, mock_supabase):
    mock_supabase.return_value.select.return_value.eq.return_value.eq.return_value.\
        execute.return_value = MagicMock(data=[{"id": 1}], count=1)

    mock_supabase.return_value.select.return_value.eq.return_value.eq.return_value.\
        execute.return_value = MagicMock(count=0)
    response = client.post(
        "/start_study_session", data={"topic_id": "1"}, follow_redirects=True
    )

    assert response.status_code == 200
