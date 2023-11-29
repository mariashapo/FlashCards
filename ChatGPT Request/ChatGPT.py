import openai
import ast

def query(prompt, api_key):
 
    openai.api_key = api_key

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=2500
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {e}"
    

# Later i will make the api key an environment variable
api_key = "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"

# Topic and currentVocab should be created dynamically
topic = "Vacation in Spain"
currentVocab = ["Hello", "Bye"] 
maxLength = 50
level = "beginner"

# Constructing the prompt
prompt = (
    f"Create 10 unique entries of English-Spanish word pairs related to the topic '{topic}', "
    f"tailored for a {level} level. Each entry should include an English word, its Spanish translation, "
    f"and a common Spanish sentence using that word. The sentence should be no longer than {maxLength} characters. "
    f"Do not duplicate these existing vocabulary entries: {', '.join(currentVocab)}. "
    f"Format each entry as a dictionary within a list, like this: "
    f"[{{'English': 'EnglishWord', 'Spanish': 'SpanishWord', 'Sentence': 'SpanishSentence'}}, ...]. "
    f"Provide exactly 10 entries."
)

# Request
response_text = query(prompt, api_key)

# Convert response to list of dictionaries
try:
    response_data = ast.literal_eval(response_text)
except Exception as e:
    print(f"Error in parsing response: {e}")

# Print and test if list is indexable
print("Full data:", '\n', response_data, '\n')
print("First english word in list:", response_data[0]['English'], '\n')