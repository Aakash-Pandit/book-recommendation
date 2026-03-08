from flask import Flask, request, jsonify
from flask_cors import CORS

from application.recommendation import top_popular_books, top_recommend_books

application = Flask(__name__)
CORS(application)

@application.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to the API!"})

@application.route("/api/popular_books", methods=["GET"])
def popular_books():
    popular_books = top_popular_books()
    return jsonify({"popular_books": popular_books})

@application.route("/api/recommend_books", methods=["POST"])
def recommend_books():
    data = request.get_json()
    name_of_books = data.get("name_of_books", [])
    number_of_recommendations = data.get("number_of_recommendations", 5)
    
    popular_books = top_recommend_books(name_of_books, number_of_recommendations)
    return jsonify({"popular_books": popular_books})