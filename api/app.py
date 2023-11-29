from flask import Flask, render_template, request, redirect
import requests

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add_word")
def add_word():
    return render_template("add_word.html")


@app.route("/display_words", methods=["POST"])
def display_words():
    word = request.form.get("word")
    translation = request.form.get("translation")
    print(word)
    print(translation)
    return render_template("display_words.html")