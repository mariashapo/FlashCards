import openai
import ast

def query():
    
    existing_vocab = ["hello", "bye"]
    api_key = "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"
    openai.api_key = api_key

    topic_name = "vacation"

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

 
    response = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=500)
    print("response: ", response)
    response_text = response.choices[0].text.strip()
    output_list = ast.literal_eval(response_text)

    print("Received response from OpenAI:", output_list)
    
query()
