import ast
from unittest.mock import MagicMock, patch

import openai
import pytest
from app import app as flask_app


# Mocks and fixtures
@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


# Mock API, such that we do not interact with real API
@pytest.fixture
def mock_openai_api():
    with patch("openai.Completion.create") as mock:
        mock.return_value = MagicMock(
            choices=[
                MagicMock(
                    text=str(
                        [
                            {
                                "English": "Hello",
                                "Spanish": "Hola",
                                "Sentence": "Hola, ¿cómo estás?",
                            }
                        ]
                    )
                )
            ]
        )
        yield mock


# Mock database, such that we do not interact with real database
@pytest.fixture
def mock_supabase(mocker):
    mocker.patch(
        "app.supabase.table",
        return_value=MagicMock(
            select=MagicMock(
                return_value=MagicMock(
                    execute=MagicMock(
                        return_value=MagicMock(
                            data=[{"word1": "Hello", "word2": "Hola"}]
                        )
                    ),
                    order=MagicMock(
                        return_value=MagicMock(
                            limit=MagicMock(
                                execute=MagicMock(
                                    return_value=MagicMock(data=[{"id": 1}])
                                )
                            )
                        )
                    ),
                    eq=MagicMock(
                        return_value=MagicMock(
                            execute=MagicMock(
                                return_value=MagicMock(
                                    data=[{"id": 1, "word1": "Hello", "word2": "Hola"}]
                                )
                            )
                        )
                    ),
                    gt=MagicMock(
                        return_value=MagicMock(
                            order=MagicMock(
                                return_value=MagicMock(
                                    limit=MagicMock(
                                        execute=MagicMock(
                                            return_value=MagicMock(data=[{"id": 2}])
                                        )
                                    )
                                )
                            )
                        )
                    ),
                )
            ),
            insert=MagicMock(
                return_value=MagicMock(execute=MagicMock(return_value=MagicMock()))
            ),
        ),
    )


# Tests for ChatGPT.py
def test_query_correct_output(mock_openai_api):
    topic = "Test Topic"
    vocab = ["Test", "Vocab"]
    result = query(topic, vocab)
    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)
    assert "English" in result[0] and "Spanish" in result[0] and "Sentence" in result[0]


def test_query_handling_exceptions(mock_openai_api):
    topic = "Test Topic"
    vocab = ["Test", "Vocab"]
    mock_openai_api.side_effect = Exception("API Error")
    result = query(topic, vocab)
    assert "Error" in result


# Tests for app.py
def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200


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


def test_generated_words_route(client, mock_openai_api, mock_supabase):
    response = client.post("/generated_words", data={"topic": "Test Topic"})
    assert response.status_code == 200


#def test_display_words_route(client, mock_supabase):
#    response = client.get("/display_words")
#    assert response.status_code == 302  # Should redirect


#def test_display_word_route(client, mock_supabase):
#    response = client.get("/display_word/1")
#    assert response.status_code == 200


def query(topic, current_vocab):
    # Later I will make the api key an environment variable
    api_key = "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"
    openai.api_key = api_key

    # Constructing the prompt
    max_length = 50
    level = "beginner"
    prompt = (
        f"Create 10 unique entries of English-Spanish word pairs related "
        f"to the topic '{topic}', tailored for a {level} level. Each entry "
        f"should include an English word, its Spanish translation, and a "
        f"common Spanish sentence using that word. The sentence should be "
        f"no longer than {max_length} characters. Do not duplicate these "
        f"existing vocabulary entries: {', '.join(current_vocab)}. Format "
        f"each entry as a dictionary within a list, like this: "
        f"[{{'English': 'EnglishWord', 'Spanish': 'SpanishWord', "
        f"'Sentence': 'SpanishSentence'}}, ...]. Provide exactly 10 entries."
    )

    try:
        response = openai.Completion.create(
            engine="text-davinci-003", prompt=prompt, max_tokens=2500
        )
        response_text = response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {e}"

    # Convert response to list of dictionaries
    try:
        response_data = ast.literal_eval(response_text)
    except Exception as e:
        print(f"Error in parsing response: {e}")

    return response_data
