# -*- coding: utf-8 -*-

# Python Standard Library
import os
from datetime import datetime

# Dependencies: Flask + PIL or Pillow
from flask import Flask, send_from_directory, redirect as redirect_flask, render_template, url_for, request
import pymongo

# Local imports
# from settings import *

app = Flask(__name__)

client = pymongo.MongoClient()
db = client.artlogic

@app.route("/")
def home():
    artworks = db.artworks.find().sort("id", -1)[:10]
    return render_template("home.html", artworks=artworks)

@app.route("/artists/")
def artists():
    artists = db.artists.find().sort("artist_sort", 1)
    return render_template("artists.html", artists=artists)

@app.route("/artists/<slug>/")
def artist(slug):
    artist = db.artists.find_one({ "slug": slug})
    artworks = db.artworks.find({"artist": artist["artist"]}).sort("id", -1)[:10]
    return render_template("artist.html", artist=artist, artworks=artworks)

@app.route('/exhibition', methods=['GET', 'POST'])
def enterexhibition():
    allexhibition = db.exhibition.find()
    artists = db.artists.find().sort("artist_sort", 1)
    exhibition = None
    new = False
    if request.method == 'POST' and 'exhibition' in request.form:
        exhibition = request.form['exhibition']
        if db.exhibition.find_one({'exhibition': exhibition}) is None:
            # this is a new exhibition, add it to the database
            db.exhibition.insert({'exhibition': exhibition})
            new = True
    return render_template('exhibition.html', exhibition=exhibition, allexhibition=allexhibition, artists=artists, new=new)


# route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            return redirect(url_for('home'))
    return render_template('exhibitions', error=error)



if __name__ == '__main__':
    app.run(debug=True)
