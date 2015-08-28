#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python Standard Library
from flask import   Flask, flash, redirect as redirect_flask, \
                    render_template, url_for, request, \
                    abort, Response, session
from flask_pagedown import PageDown

import pymongo

from .. import utils
from bson import ObjectId
from bson.json_util import dumps as bson_dumps
import forms

import config

import json

from ..utils import login_required

from ..settings import db

from flask import Blueprint, render_template, abort

blueprint = Blueprint('admin_artist', __name__)

@blueprint.route('/', methods=['GET'])
@login_required
def index():
    artists = db.artist.find()
    return render_template('admin/artist/index.html', artists=artists)

@blueprint.route('/create/', methods=['GET','POST'])
@login_required
def create():
    form = forms.ArtistForm()
    exhibitions = db.exhibitions.find()

    if request.method == 'POST':
        if form.validate():
            formdata = form.data
            artist = utils.handle_form_data({}, formdata, ['press_release_file'])
            artist['slug'] = utils.slugify(artist['name'])

            if 'press_release_file' in request.files \
                and request.files['press_release_file']:
                artist['press_release'] = utils.handle_uploaded_file(
                        request.files['press_release_file'],
                        config.upload['PRESS_RELEASE'],
                        utils.setfilenameroot(request.files['press_release_file'].filename, artist['slug'])
                    )
                artist['press_release_size'] = utils.getfilesize(artist['press_release'])

            if 'biography_file' in request.files \
                and request.files['biography_file']:
                artist['biography_file'] = utils.handle_uploaded_file(
                        request.files['biography_file'],
                        config.upload['BIOGRAPHY'],
                        utils.setfilenameroot(request.files['biography_file'].filename, artist['slug'])
                    )
                artist['biography_size'] = utils.getfilesize(artist['biography_file'])

            if 'coverimage' in request.files:
                uploaded_image = request.files.getlist('coverimage')[0]
                artist['coverimage'] = {
                    'path': utils.handle_uploaded_file(
                        uploaded_image,
                        config.upload['COVER_IMAGE'],
                        utils.setfilenameroot(uploaded_image.filename, artist['slug'])
                    )
                }
            db.artist.insert(artist)
            
            if 'image' in request.files:
                for uploaded_image in request.files.getlist('image'):
                    image = {
                        'artist': artist,
                        'path': utils.handle_uploaded_file(
                            uploaded_image,
                            config.upload['ARTWORK_IMAGE'],
                            utils.setfilenameroot(uploaded_image.filename, artist['slug'])

                        )
                    }
                    
                    db.image.insert(image)
            
            flash('You successfully created an artist page', 'success')
            
            if (request.is_xhr):
                return bson_dumps(artist), 201
            
            else:
                return redirect_flask(url_for('.index'))
            
        elif (request.is_xhr):
            # Invalid and xhr, return the errors, rather than full HTML
            return json.dumps(form.errors), 400
            
    return render_template('admin/artist/create.html', form=form, exhibitions=exhibitions)


@blueprint.route('/update/<artist_id>', methods=['GET', 'POST'])
@login_required
def update(artist_id):
    artist = db.artist.find_one({"_id": ObjectId(artist_id)})
    
    exhibitions = db.exhibitions.find()

    if request.method == 'POST':
        form = forms.ArtistForm()

        if form.validate_on_submit():
            formdata = form.data
            artist =  utils.handle_form_data(artist, formdata, ['press_release_file'])
            
            if 'press_release_file' in request.files \
                and request.files['press_release_file']:
                artist['press_release'] = utils.handle_uploaded_file(
                        request.files['press_release_file'],
                        config.upload['PRESS_RELEASE'],
                        utils.setfilenameroot(request.files['press_release_file'].filename, artist['slug'])
                    )
                artist['press_release_size'] = utils.getfilesize(artist['press_release'])
            
            if 'biography_file' in request.files \
                and request.files['biography_file']:
                artist['biography_file'] = utils.handle_uploaded_file(
                        request.files['biography_file'],
                        config.upload['BIOGRAPHY'],
                        utils.setfilenameroot(request.files['biography_file'].filename, artist['slug'])
                    )
                artist['biography_size'] = utils.getfilesize(artist['biography_file'])
            
            if 'coverimage' in request.files:
                uploaded_image = request.files.getlist('coverimage')[0]
                artist['coverimage'] = {
                    'path': utils.handle_uploaded_file(
                        uploaded_image,
                        config.upload['COVER_IMAGE'],
                        utils.setfilenameroot(uploaded_image.filename, artist['slug'])
                    )
                }
            elif 'coverimage' not in request.form:
                if 'coverimage' in artist:
                    del artist['coverimage']
            
            db.artist.update({"_id": ObjectId(artist_id)}, artist)

            ## Update this artist on images as well
            db.image.update({"artist._id": ObjectId(artist_id)}, {"$set": { "artist": artist }}, multi=True)
            ## Update this artist on exhibitions as well
            db.exhibitions.update({"artist._id": ObjectId(artist_id)}, {"$set": { "artist": artist }}, multi=True)

            # Remove images which were disabled in the form
            for image in db.image.find({"artist._id": ObjectId(artist_id)}):
                if str (image['_id']) not in request.form.getlist('image'):
                    db.image.remove({'_id': image['_id']})
            
            if 'image' in request.files:
                for uploaded_image in request.files.getlist('image'):
                    image = {
                        'artist': artist,
                        'path': utils.handle_uploaded_file(
                            uploaded_image,
                            config.upload['ARTWORK_IMAGE'],
                            utils.setfilenameroot(uploaded_image.filename, artist['slug'])

                        )
                    }
                    
                    db.image.insert(image)
            
            flash('You\'ve updated the artist page successfully', 'success')
            
            if request.is_xhr:
                return bson_dumps(artist), 201
            else:
                return redirect_flask(url_for('.index'))
        else:
            # Invalid
            if request.is_xhr:
                return json.dumps(form.errors), 400
            else:
                return render_template('admin/artist/edit.html',
                                            form=form, 
                                            images=db.image.find({"artist._id": ObjectId(artist_id)}), 
                                            exhibitions=exhibitions, 
                                            coverimage=[artist['coverimage']] if 'coverimage' in artist else [])


    else:
        form = forms.ArtistForm(data=artist)
        
    return render_template('admin/artist/edit.html',
                                form=form,
                                images=db.image.find({"artist._id": ObjectId(artist_id)}),
                                exhibitions=exhibitions,
                                coverimage=[artist['coverimage']] if 'coverimage' in artist else [])


@blueprint.route('/delete/<artist_id>', methods=['GET', 'POST'])
@login_required
def deleteArtist(artist_id):
    if request.method == 'POST':
        print artist_id
        db.artist.remove({"_id": ObjectId(artist_id)})
        flash(u'You deleted the artist page', 'warning')
        return redirect_flask(url_for('.index'))

    return render_template('admin/artist/delete.html')

"""
    Publish method, sets an artist to be published or not.
    Returns JSON version of the published artist
"""
@blueprint.route("/publish/<artist_id>", methods=['POST'])
@login_required
def publishArtist (artist_id):
    is_published = ('true' == request.form['is_published'])
    db.artist.update(
        {'_id': ObjectId(artist_id)},
        {'$set': {'is_published': is_published}}
    )
    return bson_dumps(db.artist.find_one({'_id': ObjectId(artist_id)}))
