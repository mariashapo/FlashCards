import ast
import json
import random

import openai
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from supabase import Client, create_client

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
app.secret_key = "dev"
login_manager.login_view = "login"
login_manager.init_app(app)


class SimpleUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


@login_manager.user_loader
def load_user(user_id):
    """Takes a user ID and returns a user object or None if the user does not exist."""
    if user_id is not None:
        return SimpleUser(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash("You must be logged in to view that page.")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        response = (
            supabase.table("Users").select("*").eq("username", username).execute()
        )
        try:
            print("Hey")
            if response.data[0]["password"] == password:
                login_user(SimpleUser(str(response.data[0]["id"])))
                return render_template("index.html", username=username)
            else:
                flash("Incorrect password")
                return redirect("login")
        except (TypeError, AttributeError, IndexError):
            flash("The user was not found")
            return redirect("login")
    return render_template("index.html", username=None)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        data = {"username": username, "password": password}
        response = supabase.table("Users").insert(data).execute()
        try:
            response.data[0]["username"]
            flash(f"User: {username} was properly registered")
        except (TypeError, AttributeError):
            print("Error adding flash cards to database.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Route used to allow users to logout."""
    logout_user()
    flash("You successfully logged out")
    return redirect(url_for("login"))


@app.route("/topics")
def topics():
    print(current_user.id)
    # Fetch all topics from the Topics table
    topics_data = (
        supabase.table("Topics")
        .select("id, name")
        .eq("owner_id", current_user.id)
        .execute()
    )

    # If the response contains data, convert it to a list of dictionaries
    if topics_data.data:
        topics_list = [
            {"id": topic["id"], "name": topic["name"]} for topic in topics_data.data
        ]
    else:
        topics_list = []

    # Render the index template and pass the topics list
    return render_template("topics.html", topics_list=topics_list)


@app.route("/add_new_topic", methods=["POST"])
def add_new_topic():
    # Get a new topic name from the request form data
    new_topic_name = request.form.get("newTopicName")

    # Check if the 'newTopicName' field is missing in the request data
    if new_topic_name is None:
        return jsonify({"error": "'newTopicName' field is missing in the request"}), 400

    # Validate that the new topic name is not empty or null
    if not new_topic_name.strip():
        return jsonify({"error": "Topic name cannot be empty"}), 400

    # Fetch the maximum ID from the Topics table
    # max_id is a custom SQL query defined in Supabase, which does the following:
    #   SELECT MAX(id) INTO max_id_value FROM "Topics";
    #   RETURN COALESCE(max_id_value, 0);
    max_id_result = supabase.rpc("max_id", params={}).execute()
    max_id = max_id_result.data

    # Insert the new topic into the database
    print(new_topic_name)
    insert_result = (
        supabase.table("Topics")
        .insert({"id": max_id + 1, "name": new_topic_name, "owner_id": current_user.id})
        .execute()
    )

    # Retrieve the ID of the new topic (adjust based on how your DB returns this information)
    new_topic_id = insert_result.data[0]["id"] if insert_result.data else None

    # Return the new topic's ID and name in a JSON response
    return jsonify({"id": new_topic_id, "name": new_topic_name})


@app.route("/add_word")
@login_required
def add_word():
    # Fetch corresponding topic names from Topics table
    response = (
        supabase.table("Topics")
        .select("id, name")
        .eq("owner_id", current_user.id)
        .execute()
    )
    topics = {topic["id"]: topic["name"] for topic in response.data}

    # Filter only the names of the topics that are used in Flashcards
    topics_list = [{"id": topic_id, "name": topics[topic_id]} for topic_id in topics]

    # Render the template and pass the topics list
    return render_template("add_word.html", topics_list=topics_list)


@app.route("/generate_words")
@login_required
def generate_words():
    # Fetch corresponding topic names from Topics table
    topics_data = (
        supabase.table("Topics")
        .select("id, name")
        .eq("owner_id", current_user.id)
        .execute()
    )
    topics = {topic["id"]: topic["name"] for topic in topics_data.data}

    # Filter only the names of the topics that are used in Flashcards
    topics_list = [{"id": topic_id, "name": topics[topic_id]} for topic_id in topics]
    return render_template("generate_words.html", topics_list=topics_list)


@app.route("/added_word", methods=["POST"])
@login_required
def added_word():
    word = request.form.get("word")
    translation = request.form.get("translation")
    topic_id = request.form.get("topic")
    topic_data = supabase.table("Topics").select("name").eq("id", topic_id).execute()
    topic_name = topic_data.data[0]["name"]
    # Insert data into Supabase
    data = {"word1": word, "word2": translation, "topic_id": topic_id}
    response = supabase.table("Flashcards").insert(data).execute()
    try:
        response.data[0]["word1"]
    except (TypeError, AttributeError):
        print("Error adding flash cards to database.")
    return render_template(
        "added_word.html", word=word, translation=translation, topic_name=topic_name
    )


@app.route("/generated_words", methods=["POST"])
@login_required
def generated_words():
    topic_id = request.form.get("topic")
    prompt = request.form.get("prompt")
    topic_data = supabase.table("Topics").select("name").eq("id", topic_id).execute()
    topic_name = topic_data.data[0]["name"]

    output_list = query(topic_id, prompt)

    # Render an intermediate page with a loading message
    # return render_template("loading.html")
    return render_template(
        "generated_words.html", output_list=output_list, topic_name=topic_name)


@app.route("/display_words")
@login_required
def display_words():
    words_list = supabase.table("Flashcards").select("*").execute().data
    if len(words_list) == 0:
        first_pair = None
    else:
        first_pair = words_list[0]
    return render_template(
        "display_words.html", words=json.dumps(words_list), first_pair=first_pair
    )  # Start displaying the first element of the list


background_tasks_results = {}


def query(topic_id, topic_name):
    current_vocab_pairs = (
        supabase.table("Flashcards")
        .select("word1")
        .eq("topic_id", topic_id)
        .execute()
        .data
    )
    existing_vocab = [pair["word1"] for pair in current_vocab_pairs]

    api_key = "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"
    openai.api_key = api_key

    print("The topic is: ", topic_name)
    print("The topic ID is: ", topic_id)

    prompt = (
        f"Create 5 unique entries of English-Spanish word pairs related "
        f"to the topic '{topic_name}', tailored for a beginner level. Each entry "
        f"should include an English word and its Spanish translation. "
        f"Do not include '¿' and '¡'. "
        f"Do not duplicate these existing vocabulary entries: "
        f"{', '.join(existing_vocab)}. "
        f"Format each entry as a dictionary within a list, like this: "
        f"[{{'English': 'EnglishWord', 'Spanish': 'SpanishWord'}}, ...]."
        f"Provide exactly 5 entries."
    )

    try:
        response = openai.Completion.create(
            engine="text-davinci-003", prompt=prompt, max_tokens=500
        )
        response_text = response.choices[0].text.strip()
        output_list = ast.literal_eval(response_text)

        print("Received response from OpenAI:", output_list)

        for item in output_list:
            data = {
                "word1": item["English"],
                "word2": item["Spanish"],
                "topic_id": int(topic_id),
            }
            print(data)
            response = supabase.table("Flashcards").insert(data).execute()
            print("Inserted data into database:", response.data)

    except Exception as e:
        print("Error in async_query:", str(e))
    return output_list


@app.route("/study_session/<int:word_id>")
def study_session(word_id):
    # Fetch the word details based on the provided word_id
    word_details = (
        supabase.table("Flashcards")
        .select("id", "word1", "word2")
        .eq("id", word_id)
        .execute()
        .data
    )

    if not word_details:
        # Handle the case when the word with the specified ID is not found
        return render_template("word_not_found.html")

    # Extract the word details
    record = word_details[0]
    correct_word = record["word2"]

    # Fetch three additional random word2 translations (excluding the correct word)
    random_words_data = (
        supabase.table("Flashcards")
        .select("word2")
        .neq("word2", correct_word)
        .order("id")  # Use a unique field like 'id' for randomness
        .limit(3)
        .execute()
        .data
    )

    # Extract the random words
    random_words = [word_data["word2"] for word_data in random_words_data]

    # Include the correct word in the options
    options = [correct_word] + random_words

    # Shuffle the options
    random.shuffle(options)

    # Pass data to the template, including word_id
    return render_template(
        "study_session.html",
        word=record["word1"],
        options=options,
        word_id=record["id"],
    )


@app.route("/get_correct_option/<int:word_id>", methods=["GET"])
def get_correct_option(word_id):
    # Fetch the correct option (word2) for the given word_id
    correct_option = (
        supabase.table("Flashcards")
        .select("word2")
        .eq("id", word_id)
        .limit(1)
        .execute()
        .data
    )

    if not correct_option:
        return jsonify({"error": "Word not found"}), 404

    return jsonify({"correct_option": correct_option[0]["word2"]})


@app.route("/get_next_word/<int:current_id>", methods=["GET"])
def get_next_word(current_id):
    # Mark the current word as learned
    supabase.table("Flashcards").update({"learned": True}).eq(
        "id", current_id
    ).execute()

    # Fetch a random word that the user has not learned yet
    record = (
        supabase.table("Flashcards")
        .select("*")
        .eq("learned", False)
        .order("id")  # Use a unique field like 'id' for randomness
        .limit(1)
        .execute()
        .data
    )

    if not record:
        # Handle the case when there are no more words
        return jsonify({"message": "No more words"}), 404

    return jsonify({"id": record[0]["id"]})
