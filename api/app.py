import ast

import openai
from flask import Flask, redirect, render_template, request, url_for, jsonify, flash 
from supabase import Client, create_client
import json
from flask_login import LoginManager, login_required, UserMixin

# Supabase credentials
SUPABASE_URL = "https://qfgwfjebnbvfijeaejza.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZ"
    "SIsInJlZiI6InFmZ3dmamVibmJ2ZmlqZWFlanphIiwicm9sZSI6InNlcnZp"
    "Y2Vfcm9sZSIsImlhdCI6MTcwMTI1MzQyOSwiZXhwIjoyMDE2ODI5NDI5fQ."
    "8EnvGn8JINHB5gEu0hWTKvsC7AqSDGPrH12bTBjIMT4"
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

login_manager = LoginManager()
app = Flask(__name__)
app.secret_key = 'dev'
login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """ Takes a user ID and returns a user object or None if the user does not exist."""
    if user_id is not None:
        return 1
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('login'))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        data = {"username": username, "password": password}
        response = supabase.table("Users").select("*").eq("username", username).execute()
        try:
            if response.data[0]["password"] == password:
                return render_template("index.html", username = username)
            else:
                flash("Incorrect password")
                return redirect("login")
        except (TypeError, AttributeError):
            print("Error restrieving data")
    return render_template("index.html", username = None)


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    return render_template("signup.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        data = {"username": username, "password": password}
        response = supabase.table("Users").insert(data).execute()
        try:
            response.data[0]["username"]
            flash(f'User: {username} was properly registered')
        except (TypeError, AttributeError):
            print("Error adding flash cards to database.")

    return render_template("login.html")


@app.route("/add_word")
@login_required
def add_word():
    return render_template("add_word.html")


@app.route("/generate_words")
@login_required
def generate_words():
    return render_template("generate_words.html")


@app.route("/added_word", methods=["POST"])
@login_required
def added_word():
    word = request.form.get("word")
    translation = request.form.get("translation")
    # Insert data into Supabase
    data = {"word1": word, "word2": translation}
    response = supabase.table("Flashcards").insert(data).execute()
    try:
        response.data[0]["word1"]
    except (TypeError, AttributeError):
        print("Error adding flash cards to database.")
    return render_template("added_word.html", word=word, translation=translation)


@app.route("/generated_words", methods=["POST"])
@login_required
def generated_words():
    topic = request.form.get("topic")
    current_vocab_pairs = supabase.table("Flashcards").select("word1").execute().data
    existing_vocab = [pair["word1"] for pair in current_vocab_pairs]
    # Open AI Request
    output_list = query(topic, existing_vocab)
    # Insert data into Supabase
    for item in output_list:
        data = {"word1": item["English"], "word2": item["Spanish"]}
        response = supabase.table("Flashcards").insert(data).execute()
        try:
            response.data[0]["word1"]
        except (TypeError, AttributeError):
            print("Error adding flash cards to database.")
    return render_template("generated_words.html", output_list=output_list)


@app.route("/display_words")
@login_required
def display_words():
    words_list = (
        supabase.table("Flashcards").select("*").execute().data
    )
    if len(words_list) == 0:
        first_pair = None
    else:
        first_pair = words_list[0]
    return render_template("display_words.html", words = json.dumps(words_list), first_pair = first_pair)  # Start displaying the first element of the list


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
