from flask import Flask, render_template, request, redirect
import requests
from supabase import create_client, Client

# Supabase credentials
SUPABASE_URL = 'https://qfgwfjebnbvfijeaejza.supabase.co'
SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFmZ3dmamVibmJ2ZmlqZWFlanphIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcwMTI1MzQyOSwiZXhwIjoyMDE2ODI5NDI5fQ.8EnvGn8JINHB5gEu0hWTKvsC7AqSDGPrH12bTBjIMT4'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("add_word.html")

@app.route("/add_word", methods=["POST"])
def add_word():
    word = request.form.get("word")
    translation = request.form.get("translation")
     # Insert data into Supabase
    data = {"word1": word, "word2": translation}
    response = supabase.table("Flashcards").insert(data).execute()
    print(word)
    print(translation)
    return render_template("display_words.html")


@app.route("/display_words")
def display_words():
    return render_template("display_words.html")