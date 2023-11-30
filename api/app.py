from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from supabase import create_client, Client
from ChatGPT import query

# Supabase credentials
SUPABASE_URL = 'https://qfgwfjebnbvfijeaejza.supabase.co'
SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFmZ3dmamVibmJ2ZmlqZWFlanphIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcwMTI1MzQyOSwiZXhwIjoyMDE2ODI5NDI5fQ.8EnvGn8JINHB5gEu0hWTKvsC7AqSDGPrH12bTBjIMT4'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add_word")
def add_word():
    return render_template("add_word.html")

@app.route("/generate_words")
def generate_words():
    return render_template("generate_words.html")

@app.route("/added_word", methods=["POST"])
def added_word():
    word = request.form.get("word")
    translation = request.form.get("translation")
    # Insert data into Supabase
    data = {"word1": word, "word2": translation}
    response = supabase.table("Flashcards").insert(data).execute()
    return render_template("added_word.html", word=word, translation=translation)

@app.route("/generated_words", methods=["POST"])
def generated_words():
    topic = request.form.get("topic")
    currentVocabPairs = supabase.table("Flashcards").select("word1").execute().data
    existing_vocab = [pair['word1'] for pair in currentVocabPairs] 
    # Open AI Request
    output_list = query(topic, existing_vocab)
    # Insert data into Supabase
    for i in range(len(output_list)):
        data = {"word1": output_list[i]['English'], "word2": output_list[i]['Spanish']}
        response = supabase.table("Flashcards").insert(data).execute()
    return render_template("generated_words.html", output_list=output_list)


# The /display_words route is used to fetch and redirect to the first word in your Flashcards table.
@app.route("/display_words")
def display_words():

    # Fetch the smallest id (first record)
    first_record = supabase.table("Flashcards").select("id").order('id').limit(1).execute().data

    first_id = first_record[0]['id']
    return redirect(url_for('display_word', word_id=first_id))


@app.route("/display_word/<int:word_id>")
def display_word(word_id):
    table = "Flashcards"  # Replace with your table name

    # Fetch the record with the given word_id
    record = supabase.table(table).select("*").eq('id', word_id).execute().data

    # Fetch the next record's ID for the "Next" button
    next_record = supabase.table(table).select("id").gt('id', word_id).order('id').limit(1).execute().data
    next_id = next_record[0]['id'] if next_record else None

    # Render a template with the record and the next_id
    return render_template("display_words.html", record=record[0], next_id=next_id, current_id=word_id)


def generate_words(topic):
    list = [{'English': 'Beach', 'Spanish': 'Playa', 'Sentence': 'Vamos a la playa.'}, 
{'English': 'To Relax', 'Spanish': 'Relajarse', 'Sentence': 'Voy a relajarme en España.'},
{'English': 'Arrive', 'Spanish': 'Llegar', 'Sentence': 'Llegué a España el jueves.'},
{'English': 'Hotel', 'Spanish': 'Hotel', 'Sentence': 'Reservé un hotel en España.'},
{'English': 'Holiday', 'Spanish': 'Vacaciones','Sentence': 'Voy a pasar las vacaciones en España.'},
{'English': 'Plane', 'Spanish': 'Avión', 'Sentence': 'Viajé en avión a España.'},
{'English': 'Sun', 'Spanish': 'Sol', 'Sentence': 'Disfrutamos el sol en España.'},
{'English': 'Restaurant', 'Spanish': 'Restaurante', 'Sentence': 'Fuimos al restaurante en España.'},
{'English': 'City', 'Spanish': 'Ciudad', 'Sentence': 'Exploramos la ciudad de España.'},
{'English': 'To Visit', 'Spanish': 'Visitar', 'Sentence': 'Vamos a visitar monumentos en España.'}]
    return list