import ast
import json
import os
import random

import openai
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from supabase import Client, create_client

open_ai_key = os.getenv("OPEN_AI_KEY")

# Supabase credentials

SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")

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
    # Takes a user ID and returns a user object or None if the user does not exist
    if user_id is not None:
        return SimpleUser(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    # Redirect unauthorized users to Login page
    flash("You must be logged in to view that page.")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    # If the user is being redirected to the route from '/login'
    if request.method == "POST":
        # Get the login details and attempt to find the username in supabase
        username = request.form.get("username")
        password = request.form.get("password")
        response = (
            supabase.table("Users").select("*").eq("username", username).execute()
        )
        try:
            # If username found in database and correct password was input
            if response.data[0]["password"] == password:
                login_user(SimpleUser(str(response.data[0]["id"])))
                return render_template("index.html", username=username)

            else:  # Username found but incorrect password was input
                flash("Incorrect password")
                return redirect("login")

        except IndexError:  # Username was not found in the database
            flash("The user was not found")
            return redirect("login")

    return render_template("index.html", username=None)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # If the user is being redirected to the route from '/signup'
    if request.method == "POST":
        # Get the signup details and check if username already exists in the database
        username = request.form.get("username")
        password = request.form.get("password")
        data = {"username": username, "password": password}
        check = supabase.table("Users").select("*").eq("username", username).execute()
        try:
            check.data[0]

        # If username is not present in the database
        except IndexError:
            # Insert data into the database
            response = supabase.table("Users").insert(data).execute()

            try:  # User was registered correctly
                response.data[0]["username"]
                flash(f"User: {username} was properly registered.")
                return redirect("login")

            except IndexError:  # Issue when attempting to register the user
                flash(f"Error adding user {username} to the database.")
                return redirect("signup")

        # If username already exists in the database, it cannot be accepted
        flash(
            f"Username: {username} is already in use. Please, choose a different one."
        )
        return redirect("signup")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    # Route used to allow users to logout
    logout_user()
    flash("You successfully logged out")
    return redirect(url_for("login"))


@app.route("/topics")
@login_required
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
    return render_template(
        "topics.html", topics_list=topics_list, json_topics_list=json.dumps(topics_list)
    )


@app.route("/add_new_topic", methods=["POST"])
@login_required
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
    response = (
        supabase.table("Topics")
        .select("id, name")
        .eq("owner_id", current_user.id)
        .execute()
    )

    topics = {topic["id"]: topic["name"] for topic in response.data}

    # Construct a list of topics for the dropdown
    topics_list = [{"id": topic_id, "name": topics[topic_id]} for topic_id in topics]

    # Check if there are any topics available
    has_topics = len(topics_list) > 0

    # Render the template and pass the topics list and has_topics flag
    return render_template(
        "add_word.html", topics_list=topics_list, has_topics=has_topics
    )


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
    except IndexError:
        print("Error adding flash cards to database.")

    return render_template(
        "added_word.html",
        word=word,
        translation=translation,
        topic_name=topic_name,
        topic_id=topic_id,
    )


@app.route("/generated_words", methods=["POST"])
@login_required
def generated_words():
    topic_id = request.form.get("topic")
    prompt = request.form.get("prompt")
    topic_data = supabase.table("Topics").select("name").eq("id", topic_id).execute()
    topic_name = topic_data.data[0]["name"]

    output_list = query(topic_id, prompt)

    return render_template(
        "generated_words.html", output_list=output_list, topic_name=topic_name
    )


@app.route("/display_words/<int:topic_id>")
@login_required
def display_words(topic_id):
    words_list = (
        supabase.table("Flashcards").select("*").eq("topic_id", topic_id).execute().data
    )
    if len(words_list) == 0:
        first_pair = None
    else:
        first_pair = words_list[0]
    return render_template(
        "display_words.html",
        words=json.dumps(words_list),
        first_pair=first_pair,
        list_length=len(words_list),
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
    openai.api_key = open_ai_key

    print("The topic is: ", topic_name)
    print("The topic ID is: ", topic_id)

    prompt = (
        f"Create 5 unique entries of English-Spanish word pairs related "
        f"to the topic '{topic_name}', tailored for a beginner level. Each entry "
        f"should include an English word and its Spanish translation. "
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


@app.route("/study_session_topic")
@login_required
def study_session_topic():
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
    return render_template("study_session_topic.html", topics_list=topics_list)


@app.route("/start_study_session", methods=["POST"])
@login_required
def start_study_session():
    topic_id = request.form.get("topic_id")
    # Assuming you're looking for the first word in the topic that hasn't been studied yet
    word_data = (
        supabase.table("Flashcards")
        .select("id")
        .eq("topic_id", topic_id)
        .eq("learned", False)
        .limit(1)  # Limit to 1 to get only the first result
        .execute()
    )

    first_word_id = word_data.data[0]["id"] if word_data.data else None

    # Calculate the total number of words in the topic
    total_words_data = (
        supabase.table("Flashcards")
        .select("id", count="exact")
        .eq("topic_id", topic_id)
        .execute()
    )

    total_words = total_words_data.count if total_words_data.data else 0

    # Calculate the number of learned words in the topic
    learned_words_data = (
        supabase.table("Flashcards")
        .select("id", count="exact")
        .eq("topic_id", topic_id)
        .eq("learned", True)
        .execute()
    )

    words_learned = learned_words_data.count if learned_words_data.data else 0

    # Calculate the number of words not yet learned (if needed)
    words_not_learned = total_words - words_learned

    return render_template(
        "start_study_session.html",
        first_unstudied_word=first_word_id,
        total_words=total_words,
        words_learned=words_learned,
        words_not_learned=words_not_learned,
        topic_id=topic_id,
    )


@app.route("/study_session/<int:word_id>", methods=["GET", "POST"])
@login_required
def study_session(word_id):
    topic_id = (
        supabase.table("Flashcards").select("topic_id").eq("id", word_id).execute().data
    )[0]["topic_id"]

    # a random not learned word from the same topic set
    word_details = (
        supabase.rpc("get_random_word_for_topic", {"topic_id_": topic_id})
        .execute()
        .data
    )

    # Extract the word details
    record = word_details[0]
    correct_word = record["word2"]

    # Fetch three additional random word2 translations (excluding the correct word)
    wrong_words_data = (
        supabase.rpc("get_random_words_for_same_owner", {"exclude_word_id": word_id})
        .execute()
        .data
    )

    wrong_words_translations = [i["word2"] for i in wrong_words_data]

    # Include the correct word in the options
    options = [correct_word] + wrong_words_translations

    # Shuffle the options
    random.shuffle(options)

    # Pass data to the template, including word_id
    return render_template(
        "study_session.html",
        word=record["word1"],
        options=options,
        word_id=record["word_id"],
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

    topic_id = (
        supabase.table("Flashcards")
        .select("topic_id")
        .eq("id", current_id)
        .execute()
        .data
    )[0]["topic_id"]

    # Fetch a random word that the user has not learned yet
    record = (
        supabase.rpc("get_random_word_for_topic", {"topic_id_": topic_id})
        .execute()
        .data
    )

    if not record:
        # Handle the case when there are no more words
        return jsonify({"message": "No more words"}), 404

    return jsonify({"id": record[0]["word_id"]})
