import os
import pickle

import numpy as np

_NOTEBOOKS_DIR = os.getenv("NOTEBOOKS_DIR", "notebooks")


def _load(filename: str):
    path = os.path.join(_NOTEBOOKS_DIR, filename)
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Required model file not found: {path}")


popular_df = _load("popular.pkl")
pivot_table = _load("pivot_table.pkl")
books = _load("books.pkl")
similarity_score = _load("similarity_score.pkl")


def top_popular_books():
    books_data = []
    for _, row in popular_df.iterrows():
        book_info = {
            "title": row["Book-Title"],
            "author": row["Book-Author"] if "Book-Author" in popular_df.columns else "Unknown Author",
            "image_url": row["Image-URL-M"] if "Image-URL-M" in popular_df.columns else None,
        }
        books_data.append(book_info)
    return books_data


def top_recommend_books(name_of_book: str, number_of_recommendations: int = 5):
    index = np.where(pivot_table.index == name_of_book)[0][0]
    similar_items = sorted(
        enumerate(similarity_score[index]),
        key=lambda x: x[1],
        reverse=True,
    )[1:number_of_recommendations + 1]

    suggestions = []
    for item_index, _ in similar_items:
        temp_df = books[books["Book-Title"] == pivot_table.index[item_index]].drop_duplicates("Book-Title")
        suggestions.append({
            "title": temp_df["Book-Title"].values[0],
            "author": temp_df["Book-Author"].values[0],
            "image_url": temp_df["Image-URL-M"].values[0],
        })
    return suggestions
