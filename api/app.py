import ast

import openai
from flask import Flask, redirect, render_template, request, url_for, jsonify
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
    #first_record = (
    #    supabase.table("Flashcards").select("id").order("id").limit(1).execute().data
    #)
    words_list = (
        supabase.table("Flashcards").select("*").execute().data
    )
    print(words_list)
    element_n = 0 if len(words_list) > 0 else -1
    return render_template("display_words.html", words = words_list, element_n = element_n, size_of_list = len(words_list))  # Start displaying the first element of the list


@app.route("/next_word", methods=["POST"])
def get_next_word():
    words_list = (
        supabase.table("Flashcards").select("*").execute().data
    )
    data = request.get_json()
    element_number = data.get('current_element_number')
    print(element_number)

    return jsonify({'element_n': int(element_number) + 1, 'list_of_words': words_list})



@app.route("/display_word/<int:word_id>")
def display_word(word_id):
    table = "Flashcards"
    record = supabase.table(table).select("*").eq("id", word_id).execute().data
    next_record = (
        supabase.table(table)
        .select("id")
        .gt("id", word_id)
        .order("id")
        .limit(1)
        .execute()
        .data
    )
    next_id = next_record[0]["id"] if next_record else None
    return render_template(
        "display_words.html", record=record[0], next_id=next_id, current_id=word_id
    )


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
