import pytest
from unittest.mock import patch, MagicMock
from ChatGPT import query
from app import app as flask_app


# Mocks and fixtures
@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


# Mock API, such that we do not interact with real API
@pytest.fixture
def mock_openai_api():
    with patch('openai.Completion.create') as mock:
        mock.return_value = MagicMock(choices=[MagicMock(text=str([{
            'English': 'Hello', 'Spanish': 'Hola',
            'Sentence': 'Hola, ¿cómo estás?'
        }]))])
        yield mock


# Mock database, such that we do not interact with real database
@pytest.fixture
def mock_supabase(mocker):
    mocker.patch('app.supabase.table', return_value=MagicMock(
        select=MagicMock(return_value=MagicMock(
            execute=MagicMock(
                return_value=MagicMock(data=[{'word1': 'Hello', 'word2':
                                              'Hola'}])
            ),
            order=MagicMock(return_value=MagicMock(
                limit=MagicMock(
                    execute=MagicMock(return_value=MagicMock(data=[{'id': 1}]))
                )
            )),
            eq=MagicMock(return_value=MagicMock(
                execute=MagicMock(
                    return_value=MagicMock(data=[{
                        'id': 1, 'word1': 'Hello', 'word2': 'Hola'
                    }])
                )
            )),
            gt=MagicMock(return_value=MagicMock(
                order=MagicMock(return_value=MagicMock(
                    limit=MagicMock(
                        execute=MagicMock(return_value=MagicMock(
                            data=[{'id': 2}]))
                    )
                ))
            )),
        )),
        insert=MagicMock(return_value=MagicMock(
            execute=MagicMock(return_value=MagicMock())
        ))
    ))


# Tests for ChatGPT.py
def test_query_correct_output(mock_openai_api):
    topic = "Test Topic"
    vocab = ["Test", "Vocab"]
    result = query(topic, vocab)
    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)
    assert ('English' in result[0] and 'Spanish' in result[0] and
            'Sentence' in result[0])


def test_query_handling_exceptions(mock_openai_api):
    topic = "Test Topic"
    vocab = ["Test", "Vocab"]
    mock_openai_api.side_effect = Exception("API Error")
    result = query(topic, vocab)
    assert "Error" in result


# Tests for app.py
def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200


def test_add_word_route(client):
    response = client.get('/add_word')
    assert response.status_code == 200


def test_generate_words_route(client):
    response = client.get('/generate_words')
    assert response.status_code == 200


def test_added_word_route(client, mock_supabase):
    response = client.post('/added_word', data={'word': 'test', 'translation':
                                                'prueba'})
    assert response.status_code == 200


def test_generated_words_route(client, mock_openai_api, mock_supabase):
    response = client.post('/generated_words', data={'topic': 'Test Topic'})
    assert response.status_code == 200


def test_display_words_route(client, mock_supabase):
    response = client.get('/display_words')
    assert response.status_code == 302  # Should redirect


def test_display_word_route(client, mock_supabase):
    response = client.get('/display_word/1')
    assert response.status_code == 200
