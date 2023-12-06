import ast
from unittest.mock import MagicMock, patch

import openai
import pytest

# Assuming your Flask app is named 'flask_app'
from app import app as flask_app


# Mocks and fixtures
@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


# Mock API to not interact with real OpenAI API
@pytest.fixture
def mock_openai_api():
    with patch("openai.Completion.create") as mock:
        mock.return_value = MagicMock(
            choices=[
                MagicMock(
                    text=str(
                        [
                            {"English": "Hello", "Spanish": "Hola"},
                            {"English": "Hell", "Spanish": "Hol"},
                        ]
                    )
                )
            ]
        )
        yield mock


# Mock database to not interact with real Supabase
@pytest.fixture
def mock_supabase(mocker):
    # Mock the 'insert' method to simulate a successful database operation
    mocked_insert = MagicMock(
        return_value=MagicMock(
            execute=MagicMock(
                return_value=MagicMock(
                    data=[{"word1": "test", "word2": "prueba", "topic_id": 1, "id": 1}]
                )
            )
        )
    )

    # Mock the 'select', 'eq', 'order', and 'limit' methods as before
    mocked_table = MagicMock(
        insert=mocked_insert,
        select=MagicMock(
            return_value=MagicMock(
                execute=MagicMock(
                    return_value=MagicMock(data=[{"word1": "Hello", "word2": "Hola"}])
                )
            )
        ),
    )

    mocker.patch("app.supabase.table", return_value=mocked_table)


# Test cases
def test_query_correct_output(mock_openai_api):
    topic = "Test Topic"
    vocab = ["Test", "Vocab"]
    result = query(topic, vocab)
    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)
    assert "English" in result[0] and "Spanish" in result[0]


def test_query_handling_exceptions(mock_openai_api):
    topic = "Test Topic"
    vocab = ["Test", "Vocab"]
    mock_openai_api.side_effect = Exception("API Error")
    result = query(topic, vocab)
    assert "Error" in result


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200


"""
def test_add_word_route(client):
    response = client.get("/add_word")
    assert response.status_code == 200


def test_generate_words_route(client):
    response = client.get("/generate_words")
    assert response.status_code == 200


def test_added_word_route(client, mock_supabase):
    response = client.post(
        "/added_word", data={"word": "test", "translation": "prueba"}
    )
    assert response.status_code == 200


def test_generated_words_route(client):
    response = client.post(
        "/generated_words", data={"topic": "Test Topic", "prompt": "Test Prompt"}
    )
    assert response.status_code == 200
"""


def query(topic, current_vocab):
    # Later I will make the api key an environment variable
    api_key = "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"
    openai.api_key = api_key

    # Constructing the prompt
    prompt = (
        f"Create 10 unique entries of English-Spanish word pairs related "
        f"to the topic '{topic}', tailored for a beginner level. Each entry "
        f"should include an English word and its Spanish translation. "
        f"Do not duplicate these existing vocabulary entries: "
        f"{', '.join(current_vocab)}. Provide exactly 10 entries."
    )

    try:
        response = openai.Completion.create(
            engine="text-davinci-003", prompt=prompt, max_tokens=2500
        )
        response_text = response.choices[0].text.strip()
        response_data = ast.literal_eval(response_text)
        return response_data
    except Exception as e:
        return f"Error: {e}"
