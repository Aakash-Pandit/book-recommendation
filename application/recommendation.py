import pickle

import numpy as np

popular_df = pickle.load(open("notebooks/popular.pkl", "rb"))

pivot_table = pickle.load(open("notebooks/pivot_table.pkl", "rb"))
books = pickle.load(open("notebooks/books.pkl", "rb"))
similarity_score = pickle.load(open("notebooks/similarity_score.pkl", "rb"))

def top_popular_books():
    books_data = []
    for _, row in popular_df.iterrows():
        book_info = {
            "title": row["Book-Title"],
            "author": row["Book-Author"] if "Book-Author" in popular_df.columns else "Unknown Author",
            "image_url": row["Image-URL-M"] if "Image-URL-M" in popular_df.columns else None
        }
        books_data.append(book_info)
    
    return books_data

def top_recommend_books(name_of_books, number_of_recommendations=5):
    suggestions = []

    index = np.where(pivot_table.index == name_of_books)[0][0]
    similar_items = sorted(list(enumerate(similarity_score[index])), key=lambda x: x[1], reverse=True)[1:number_of_recommendations + 1]

    for index, avg_rating in similar_items:
        data = {}
        
        temp_df = books[books["Book-Title"] == pivot_table.index[index]]
        data["title"] = list(temp_df.drop_duplicates("Book-Title")["Book-Title"].values)[0]
        data["author"] = list(temp_df.drop_duplicates("Book-Title")["Book-Author"].values)[0]
        data["images"] = list(temp_df.drop_duplicates("Book-Title")["Image-URL-M"].values)[0]
        
        suggestions.append(data)
    return suggestions