# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import sys
from models.models import Artist, Show, Venue
from datetime import datetime
from forms import *
from flask_wtf import Form
from logging import Formatter, FileHandler
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.sql import label
from flask_moment import Moment
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
import babel
import dateutil.parser
import json
from flask_migrate import Migrate
import collections
import collections.abc
collections.Callable = collections.abc.Callable
# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
migrate = Migrate()
app.app_context().push()
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
db.init_app(app)
migrate.init_app(app, db)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
    format = "EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
    format = "EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route('/')
def index():
  return render_template('pages/home.html')


@app.route('/venues')
def venues():
  data = []
  upcoming_shows = []
  # query by city and state, group by city state
  areas = db.session.query(Venue.city, Venue.state).group_by(
      Venue.city, Venue.state).all()
  # iterate over the results, add city and state to the obj dict, then query the venues by the city in iteration
  # iterate over the venues, add the fields to another dict, append to arr
  # then add the venues arr to the obj dict, append obj to the data array
  for area in areas:
    obj = dict()
    arr = []
    venues = db.session.query(
        Venue.id, Venue.name).filter_by(city=area.city).all()
    obj['city'] = area.city
    obj['state'] = area.state
    for venue in venues:
      ven = dict()
      ven['id'] = venue.id
      ven['name'] = venue.name
      ven['num_upcoming_shows'] = Show.query.join(
          Venue).filter(Show.venue_id == venue.id).filter(Show.start_time > datetime.utcnow()).count()
      arr.append(ven)
    obj['venues'] = arr
    data.append(obj)

  return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
  # lowercase the seachterm and use ilike to allow for a case insensitive query
  search_term = request.form.get('search_term').lower()
  results = Venue.query.filter(Venue.name.ilike("%" + search_term + "%")).all()

  response = {
      "count": len(results),
      "data": []
  }
  # iterate over the results, add fields to a dict, append obj to response.data arr
  for result in results:
    obj = dict()
    obj['id'] = result.id
    obj['name'] = result.name
    obj['num_upcoming_shows'] = Show.query.join(
        Venue).filter(Show.venue_id == result.id).filter(Show.start_time > datetime.utcnow()).count()
    response['data'].append(obj)

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = db.session.query(Venue).get(venue_id)
  # join Show with Venue and filter by the venue_id
  shows = Show.query.join(Venue).filter(
      Show.venue_id == venue_id).all()
  past_shows = []
  upcoming_shows = []
  # iterate over the show, query the artist for the show, add fields to a dict then apppend the obj
  # to either past or upcoming shows
  for show in shows:
    obj = dict()
    artist = Artist.query.get(show.artist_id)
    obj['artist_id'] = show.artist_id
    obj['artist_name'] = artist.name
    obj['artist_image_link'] = artist.image_link
    obj['start_time'] = format_datetime(
        show.start_time.strftime("%m/%d/%Y, %H:%M"))
    if show.start_time < datetime.now():
      past_shows.append(obj)
    else:
      upcoming_shows.append(obj)

# form the response based on the data above
  data = dict()
  data['id'] = venue.id
  data['name'] = venue.name
  data['genres'] = venue.genres
  data['address'] = venue.address
  data['city'] = venue.city
  data['state'] = venue.state
  data['phone'] = venue.phone
  data['website'] = venue.website_link
  data['facebook_link'] = venue.facebook_link
  data['seeking_talent'] = venue.seeking_talent
  data['seeking_description'] = venue.seeking_description
  data['image_link'] = venue.image_link
  data['past_shows'] = past_shows
  data['upcoming_shows'] = upcoming_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows_count'] = len(upcoming_shows)

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # create the venue from the form, handle errors and close db session
  error = False
  try:
    form = VenueForm()
    data = form.data
    name = data['name']
    city = data['city']
    state = data['state']
    address = data['address']
    phone = data['phone']
    genres = data['genres']
    image_link = data['image_link']
    facebook_link = data['facebook_link']
    website_link = data['website_link']
    seeking_talent = data['seeking_talent']
    seeking_description = data['seeking_description']
    venue = Venue(name=name, city=city, state=state, address=address, phone=phone,
                  genres=genres, image_link=image_link, facebook_link=facebook_link,
                  website_link=website_link, seeking_talent=seeking_talent, seeking_description=seeking_description)
    db.session.add(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
    if not error:
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    else:
      flash('An error occurred. Venue ' + data.name + ' could not be listed.')

  return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # delete venue and commit, handle errors and close db session
  error = False
  try:
    venue = db.session.get(Venue, venue_id)
    db.session.delete(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
    if not error:
      flash('Venue was successfully deleted!')
    else:
      flash('An error occurred. Venue could not be deleted.')

  return None

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
  artists = Artist.query.all()
  data = []
  for artist in artists:
    obj = dict()
    obj['id'] = artist.id
    obj['name'] = artist.name
    data.append(obj)

  return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
  # search artist case insensitve using ilike after lowercasing the serach term
  search_term = request.form.get('search_term').lower()
  results = Artist.query.filter(
      Artist.name.ilike("%" + search_term + "%")).all()

  response = {
      "count": len(results),
      "data": []
  }
  # iterate over the results, add fields including the upcoming shows by joining Show with Venue where show id matches
  # the result in iteration id and the start time is greater than now, then call count
  for result in results:
    obj = dict()
    obj['id'] = result.id
    obj['name'] = result.name
    obj['num_upcoming_shows'] = Show.query.join(
        Venue).filter(Show.id == result.id).filter(Show.start_time > datetime.utcnow()).count()
    response['data'].append(obj)
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # get artist by id, then join Show and Arist where show id matches artist_id
  artist = db.session.query(Artist).get(artist_id)
  shows = Show.query.join(Artist).filter(
      Show.artist_id == artist_id).all()
  past_shows = []
  upcoming_shows = []
  # iterate over the shows to create a dict to add appropriate fields
  for show in shows:
    obj = dict()
    venue = Venue.query.get(show.venue_id)
    obj['venue_id'] = show.venue_id
    obj['venue_name'] = venue.name
    obj['venue_image_link'] = venue.image_link
    obj['start_time'] = format_datetime(
        show.start_time.strftime("%m/%d/%Y, %H:%M"))
    if show.start_time < datetime.now():
      past_shows.append(obj)
    else:
      upcoming_shows.append(obj)

  # generate the response using the above
  data = dict()
  data['id'] = artist.id
  data['name'] = artist.name
  data['genres'] = artist.genres
  data['city'] = artist.city
  data['state'] = artist.state
  data['phone'] = artist.phone
  data['website'] = artist.website_link
  data['facebook_link'] = artist.facebook_link
  data['seeking_venue'] = artist.seeking_venues
  data['seeking_description'] = artist.seeking_description
  data['image_link'] = artist.image_link
  data['past_shows'] = past_shows
  data['upcoming_shows'] = upcoming_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows_count'] = len(upcoming_shows)
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  form = ArtistForm(obj=artist)
  return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # query by artist id, then update the artist and commit, handle errors and close db session
  artist = Artist.query.get(artist_id)
  error = False
  try:
    form = ArtistForm()
    data = form.data
    artist.name = data['name']
    artist.city = data['city']
    artist.state = data['state']
    artist.phone = data['phone']
    artist.genres = data['genres']
    artist.image_link = data['image_link']
    artist.facebook_link = data['facebook_link']
    artist.website_link = data['website_link']
    artist.seeking_venues = data['seeking_venue']
    artist.seeking_description = data['seeking_description']
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
    if not error:
      flash('Artist ' + request.form['name'] + ' was successfully updated!')
    else:
      flash('An error occurred. Artist ' +
            data['name'] + ' could not be updated.')

  return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  form = VenueForm(obj=venue)
  return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # query by venue id, then update the venue and commit, handle errors and close db session
  venue = Venue.query.get(venue_id)
  error = False
  try:
    form = VenueForm()
    data = form.data
    venue.name = data['name']
    venue.city = data['city']
    venue.state = data['state']
    venue.address = data['address']
    venue.phone = data['phone']
    venue.genres = data['genres']
    venue.image_link = data['image_link']
    venue.facebook_link = data['facebook_link']
    venue.website_link = data['website_link']
    venue.seeking_talent = data['seeking_talent']
    venue.seeking_description = data['seeking_description']
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
    if not error:
      flash('Venue ' + request.form['name'] + ' was successfully updated!')
    else:
      flash('An error occurred. Venue ' +
            data['name'] + ' could not be updated.')
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # create artist, commit the result, handle errors and close db session
  error = False
  try:
    form = ArtistForm()
    data = form.data
    name = data['name']
    city = data['city']
    state = data['state']
    phone = data['phone']
    genres = data['genres']
    image_link = data['image_link']
    facebook_link = data['facebook_link']
    website_link = data['website_link']
    seeking_venues = data['seeking_venue']
    seeking_description = data['seeking_description']
    artist = Artist(name=name, city=city, state=state, phone=phone,
                    genres=genres, image_link=image_link, facebook_link=facebook_link,
                    website_link=website_link, seeking_venues=seeking_venues, seeking_description=seeking_description)
    db.session.add(artist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
    if not error:
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    else:
      flash('An error occurred. Artist ' +
            data['name'] + ' could not be listed.')

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  shows = Show.query.all()
  for show in shows:
    obj = dict()
    venue = Venue.query.get(show.venue_id)
    artist = Artist.query.get(show.artist_id)
    obj['venue_id'] = show.venue_id
    obj['venue_name'] = venue.name
    obj['artist_id'] = artist.id
    obj['artist_image_link'] = artist.image_link
    obj['start_time'] = format_datetime(
        show.start_time.strftime("%m/%d/%Y, %H:%M"))
    data.append(obj)

  return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # create show, commit the result, handle errors and close db session
  error = False
  try:
    form = ShowForm()
    data = form.data
    artist_id = data['artist_id']
    venue_id = data['venue_id']
    start_time = data['start_time']
    show = Show(artist_id=artist_id, venue_id=venue_id,
                start_time=start_time)
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
    if not error:
      flash('Show was successfully listed!')
    else:
      flash('An error occurred. Show could not be listed.')

  return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
  return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
  return render_template('errors/500.html'), 500


if not app.debug:
  file_handler = FileHandler('error.log')
  file_handler.setFormatter(
      Formatter(
          '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
  )
  app.logger.setLevel(logging.INFO)
  file_handler.setLevel(logging.INFO)
  app.logger.addHandler(file_handler)
  app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
  app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
