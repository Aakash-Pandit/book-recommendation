from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

MOCK_POPULAR_BOOKS = [
    {"title": "Harry Potter", "author": "J.K. Rowling", "image_url": "http://example.com/hp.jpg"},
    {"title": "The Hobbit", "author": "J.R.R. Tolkien", "image_url": "http://example.com/hobbit.jpg"},
]

MOCK_RECOMMENDATIONS = [
    {"title": "The Hobbit", "author": "J.R.R. Tolkien", "image_url": "http://example.com/hobbit.jpg"},
    {"title": "Dune", "author": "Frank Herbert", "image_url": "http://example.com/dune.jpg"},
]


@pytest.fixture
def client():
    with patch("application.recommendation.popular_df"), \
         patch("application.recommendation.pivot_table"), \
         patch("application.recommendation.books"), \
         patch("application.recommendation.similarity_score"):
        from application.api import application
        yield TestClient(application)


# --- GET / ---

def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Book Recommendation API!"}


# --- GET /api/popular_books ---

def test_popular_books_returns_200(client):
    with patch("application.api.top_popular_books", return_value=MOCK_POPULAR_BOOKS):
        response = client.get("/api/popular_books")
    assert response.status_code == 200


def test_popular_books_response_structure(client):
    with patch("application.api.top_popular_books", return_value=MOCK_POPULAR_BOOKS):
        response = client.get("/api/popular_books")
    assert "popular_books" in response.json()


def test_popular_books_returns_list(client):
    with patch("application.api.top_popular_books", return_value=MOCK_POPULAR_BOOKS):
        data = client.get("/api/popular_books").json()
    assert isinstance(data["popular_books"], list)


def test_popular_books_content(client):
    with patch("application.api.top_popular_books", return_value=MOCK_POPULAR_BOOKS):
        data = client.get("/api/popular_books").json()
    assert data["popular_books"] == MOCK_POPULAR_BOOKS


def test_popular_books_empty(client):
    with patch("application.api.top_popular_books", return_value=[]):
        data = client.get("/api/popular_books").json()
    assert data["popular_books"] == []


# --- POST /api/recommend_books ---

def test_recommend_books_returns_200(client):
    with patch("application.api.top_recommend_books", return_value=MOCK_RECOMMENDATIONS):
        response = client.post("/api/recommend_books", json={"name_of_book": "Harry Potter"})
    assert response.status_code == 200


def test_recommend_books_response_structure(client):
    with patch("application.api.top_recommend_books", return_value=MOCK_RECOMMENDATIONS):
        data = client.post("/api/recommend_books", json={"name_of_book": "Harry Potter"}).json()
    assert "recommendations" in data


def test_recommend_books_content(client):
    with patch("application.api.top_recommend_books", return_value=MOCK_RECOMMENDATIONS):
        data = client.post("/api/recommend_books", json={"name_of_book": "Harry Potter"}).json()
    assert data["recommendations"] == MOCK_RECOMMENDATIONS


def test_recommend_books_default_count(client):
    with patch("application.api.top_recommend_books", return_value=MOCK_RECOMMENDATIONS) as mock_fn:
        client.post("/api/recommend_books", json={"name_of_book": "Harry Potter"})
    mock_fn.assert_called_once_with("Harry Potter", 5)


def test_recommend_books_custom_count(client):
    with patch("application.api.top_recommend_books", return_value=MOCK_RECOMMENDATIONS) as mock_fn:
        client.post("/api/recommend_books", json={"name_of_book": "Dune", "number_of_recommendations": 3})
    mock_fn.assert_called_once_with("Dune", 3)


def test_recommend_books_missing_body(client):
    response = client.post("/api/recommend_books", json={})
    assert response.status_code == 422


def test_recommend_books_invalid_count_type(client):
    response = client.post("/api/recommend_books", json={"name_of_book": "Dune", "number_of_recommendations": "abc"})
    assert response.status_code == 422


def test_recommend_books_count_zero_rejected(client):
    response = client.post("/api/recommend_books", json={"name_of_book": "Dune", "number_of_recommendations": 0})
    assert response.status_code == 422


def test_recommend_books_negative_count_rejected(client):
    response = client.post("/api/recommend_books", json={"name_of_book": "Dune", "number_of_recommendations": -1})
    assert response.status_code == 422


def test_recommend_books_count_above_max_rejected(client):
    response = client.post("/api/recommend_books", json={"name_of_book": "Dune", "number_of_recommendations": 51})
    assert response.status_code == 422


def test_recommend_books_unknown_book_returns_400(client):
    with patch("application.api.top_recommend_books", side_effect=IndexError):
        response = client.post("/api/recommend_books", json={"name_of_book": "Unknown Book XYZ"})
    assert response.status_code == 400
    assert "not available" in response.json()["detail"]
