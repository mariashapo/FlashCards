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
    # Fetch all topics from the Topics table
    topics_data = supabase.table("Topics").select("id, name").execute()

    # If the response contains data, convert it to a list of dictionaries
    if topics_data.data:
        topics_list = [{"id": topic["id"], "name": topic["name"]} for topic in topics_data.data]
    else:
        topics_list = []

    # Render the index template and pass the topics list
    return render_template("index.html", topics_list=topics_list)


@app.route('/add_new_topic', methods=['POST'])
def add_new_topic():
    # Get the new topic name from the request form data
    new_topic_name = request.form.get('newTopicName')

    # Check if the 'newTopicName' field is missing in the request data
    if new_topic_name is None:
        return jsonify({"error": "'newTopicName' field is missing in the request"}), 400

    # Validate that the new topic name is not empty or null
    if not new_topic_name.strip():
        return jsonify({"error": "Topic name cannot be empty"}), 400
    
    max_id_result = supabase.rpc('max_id', params={}).execute()
    max_id=max_id_result.data

    # Insert the new topic into the database
    # This is an example; adjust according to your database schema
    print(new_topic_name)
    insert_result = supabase.table("Topics").insert({"id":max_id+1,"name": new_topic_name}).execute()

    # Retrieve the ID of the new topic (adjust based on how your DB returns this information)
    new_topic_id = insert_result.data[0]['id'] if insert_result.data else None

    # Return the new topic's ID and name in a JSON response
    return jsonify({'id': new_topic_id, 'name': new_topic_name})

@app.route('/add_word')
def add_word():
    # Call the custom SQL function using rpc with an empty params argument
    response = supabase.rpc('get_distinct_topic_ids', params={}).execute()

    # Extract topic_ids from the response
    unique_topic_ids = [row for row in response.data]

    # Fetch corresponding topic names from Topics table
    topics_data = supabase.table("Topics").select("id, name").execute()
    topics = {topic['id']: topic['name'] for topic in topics_data.data}

    # Filter only the names of the topics that are used in Flashcards
    topics_list = [{'id': topic_id, 'name': topics[topic_id]} for topic_id in unique_topic_ids if topic_id in topics]

    # Render the template and pass the topics list
    return render_template("add_word.html", topics_list=topics_list)


@app.route("/generate_words")
def generate_words():
    return render_template("generate_words.html")


@app.route("/added_word", methods=["POST"])
def added_word():
    word = request.form.get("word")
    translation = request.form.get("translation")
    topic_id = request.form.get("topic")
    topic_data = supabase.table("Topics").select("name").eq("id", topic_id).execute()
    topic_name=topic_data.data[0]['name']
    # Insert data into Supabase
    data = {"word1": word, "word2": translation, "topic_id": topic_id}
    response = supabase.table("Flashcards").insert(data).execute()
    try:
        response.data[0]["word1"]
    except (TypeError, AttributeError):
        print("Error adding flash cards to database.")
    return render_template("added_word.html", word=word, translation=translation, topic_name=topic_name)


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
    first_record = (
        supabase.table("Flashcards").select("id").order("id").limit(1).execute().data
    )
    first_id = first_record[0]["id"]
    return redirect(url_for("display_word", word_id=first_id))


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
