from ChatGPT import query
from flask import Flask, redirect, render_template, request, url_for
from supabase import Client, create_client

# Supabase credentials
SUPABASE_URL = 'https://qfgwfjebnbvfijeaejza.supabase.co'
SUPABASE_ANON_KEY = (
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZ'
    'SIsInJlZiI6InFmZ3dmamVibmJ2ZmlqZWFlanphIiwicm9sZSI6InNlcnZp'
    'Y2Vfcm9sZSIsImlhdCI6MTcwMTI1MzQyOSwiZXhwIjoyMDE2ODI5NDI5fQ.'
    '8EnvGn8JINHB5gEu0hWTKvsC7AqSDGPrH12bTBjIMT4'
)

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
    try:
        response.data[0]['word1']
    except (TypeError, AttributeError):
        print("Error adding flash cards to database.")
    return render_template("added_word.html", word=word,
                           translation=translation)


@app.route("/generated_words", methods=["POST"])
def generated_words():
    topic = request.form.get("topic")
    current_vocab_pairs = supabase.table("Flashcards")\
        .select("word1").execute().data
    existing_vocab = [pair['word1'] for pair in current_vocab_pairs]
    # Open AI Request
    output_list = query(topic, existing_vocab)
    # Insert data into Supabase
    for item in output_list:
        data = {"word1": item['English'], "word2": item['Spanish']}
        response = supabase.table("Flashcards").insert(data).execute()
        try:
            response.data[0]['word1']
        except (TypeError, AttributeError):
            print("Error adding flash cards to database.")
    return render_template("generated_words.html", output_list=output_list)


@app.route("/display_words")
def display_words():
    first_record = supabase.table("Flashcards").select("id").order('id')\
        .limit(1).execute().data
    first_id = first_record[0]['id']
    return redirect(url_for('display_word', word_id=first_id))


@app.route("/display_word/<int:word_id>")
def display_word(word_id):
    table = "Flashcards"
    record = supabase.table(table).select("*").eq('id', word_id).execute().data
    next_record = supabase.table(table).select("id").gt('id', word_id)\
        .order('id').limit(1).execute().data
    next_id = next_record[0]['id'] if next_record else None
    return render_template("display_words.html", record=record[0],
                           next_id=next_id, current_id=word_id)
