from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
# from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Items, User

from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import urllib
from flickrapi import FlickrAPI

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"

engine = create_engine('sqlite:///categoriesitems.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Flicker Image Retrive
def imageRetrive(category, item):
    Flickr_Search_url = 'https://api.flickr.com/services/rest'
    FLICKR_PUBLIC = '4811a3455ae17c912fdcf708b2033b95'
    FLICKR_SECRET = '34307446edc1b1d0'
    if item == '':
        tags = category
    else:
        tags = category + ',' + item
    flickr = FlickrAPI(FLICKR_PUBLIC, FLICKR_SECRET, format='parsed-json')
    response = flickr.photos.search(tags=tags, tag_mode='all', per_page=1,
    extras='url_sq', page=1, media='photos')
    print response
    if response['stat'] != "ok" or response['photos']['total'] == '0':
        print "Flicker Search Error Code - " + response['stat']
        return None
    else:
        return response['photos']['photo'][0]['url_sq']


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['gplus_id']
        del login_session['provider']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'username' in login_session:
        gdisconnect()
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategories'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategories'))


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Jason APIs


# All Categories JSON API
@app.route('/categories/JSON')
def showCategoriesJSON():
    categories = session.query(Category).all()
    return jsonify(Category=[i.serialize for i in categories])


# List items in Category JSON API
@app.route('/categories/<int:category_id>/list/JSON')
def categoryListJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Items).filter_by(
        category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])


# Item JSON API
@app.route('/categories/<int:category_id>/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Items).filter_by(id=item_id).one()
    return jsonify(Items=[item.serialize])


# Show all Categories
@app.route('/')
@app.route('/categories')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return render_template('publiccategories.html', categories=categories)
    else:
        return render_template('categories.html', categories=categories)


# Categories Functions

# Create new category
@app.route('/categories/new', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'], image=imageRetrive(request.form['name'], ''), user_id=login_session['user_id'])
        session.add(newCategory)
        session.commit()
        flash("New category %s successfully created!" % newCategory.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('newcategory.html')


# Edit Category
@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own category in order to edit it.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            editedCategory.image = image=imageRetrive(request.form['name'], '')
            session.add(editedCategory)
            session.commit()
            flash("Category %s Successfuly Updated!" % editedCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('editcategory.html', category=editedCategory)


# Delete Category
@app.route('/categories/<int:category_id>/delete', methods=['GET', 'POST'])
def deleteCategory(category_id):
    deletedCategory = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if deletedCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this category. Please create your own category in order to delete it.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(deletedCategory)
        session.commit()
        flash("%s Category Successfuly Deleted!" % deletedCategory.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('deletecategory.html', category=deletedCategory)


# Show categoy's items list
@app.route('/categories/<int:category_id>/')
@app.route('/categories/<int:category_id>/list')
def categoryList(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Items).filter_by(category_id=category_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publiclist.html', items=items, category=category, creator=creator)
    else:
        return render_template('list.html', category=category, items=items,
        creator=creator)

# Create new item
@app.route('/categories/<int:category_id>/new', methods=['GET', 'POST'])
def newItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized to add items to this category. Please create your own category in order to add items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        newItem = Items(name=request.form['name'], description=request.form[
                           'description'], image=imageRetrive(category.name, request.form['name']), category_id=category_id, user_id=category.user_id)
        session.add(newItem)
        session.commit()
        flash("New Item %s Succesffuly Created!" % newItem.name)
        return redirect(url_for('categoryList', category_id=category.id))
    else:
        return render_template('newitem.html', category=category, category_id=category.id)


# Edit an item
@app.route('/categories/<int:category_id>/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    editedItem = session.query(Items).filter_by(id=item_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit  items on this category. Please create your own category in order to edit items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form.get('name'):
            editedItem.name = request.form['name']
            editedItem.image=imageRetrive(category.name, request.form['name'])
        if request.form.get('description'):
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash("%s Item Successfuly Edited" % editedItem.name)
        return redirect(url_for('categoryList',category_id=category.id))
    else:
        return render_template(
            'edititem.html', item=editedItem, category=category, category_id=category_id)


@app.route('/categories/<int:category_id>/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    itemToDelete = session.query(Items).filter_by(id=item_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete  items on this category. Please create your own category in order to delete items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Item %s Successfuly Deleted" % itemToDelete.name)
        return redirect(url_for('categoryList', category_id=category_id))
    else:
        return render_template('deleteitem.html', item=itemToDelete, category=category)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
