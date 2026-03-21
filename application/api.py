from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from application.recommendation import top_popular_books, top_recommend_books
from application.middleware_logger import LoggingMiddleware

application = FastAPI()
application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

application.add_middleware(LoggingMiddleware)


class RecommendRequest(BaseModel):
    name_of_book: str
    number_of_recommendations: int = 5


@application.get("/")
def home():
    return {"message": "Welcome to Book Recommendation System!"}


@application.get("/api/popular_books")
def popular_books():
    return {"popular_books": top_popular_books()}


@application.post("/api/recommend_books")
def recommend_books(body: RecommendRequest):
    try:
        recommendations = top_recommend_books(body.name_of_book, body.number_of_recommendations)
    except IndexError:
        raise HTTPException(status_code=400, detail="This book is not available in list")
    return {"popular_books": recommendations}