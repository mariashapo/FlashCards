from flask import Flask, render_template, request, redirect
import requests

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("add_word.html")

@app.route("/add_word", methods=["POST"])
def add_word():
    word = request.form.get("word")
    translation = request.form.get("translation")
    print(word)
    print(translation)
    return render_template("display_words.html")


@app.route("/display_words")
def display_words():
    return render_template("display_words.html")