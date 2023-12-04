import ast
import openai
from flask import Flask, render_template, request, jsonify
from supabase import Client, create_client
import random
import json

# Supabase credentials
SUPABASE_URL = "https://qfgwfjebnbvfijeaejza.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZ"
    "SIsInJlZiI6InFmZ3dmamVibmJ2ZmlqZWFlanphIiwicm9sZSI6InNlcnZp"
    "Y2Vfcm9sZSIsImlhdCI6MTcwMTI1MzQyOSwiZXhwIjoyMDE2ODI5NDI5fQ."
    "8EnvGn8JINHB5gEu0hWTKvsC7AqSDGPrH12bTBjIMT4"
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
        response.data[0]["word1"]
    except (TypeError, AttributeError):
        print("Error adding flash cards to database.")
    return render_template("added_word.html", word=word, translation=translation)


@app.route("/generated_words", methods=["POST"])
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
def display_words():
    words_list = supabase.table("Flashcards").select("*").execute().data
    if len(words_list) == 0:
        first_pair = None
    else:
        first_pair = words_list[0]
    return render_template(
        "display_words.html", words=json.dumps(words_list), first_pair=first_pair
    )  # Start displaying the first element of the list


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
