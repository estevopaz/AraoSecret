#!/usr/bin/env python3
# coding: utf-8
'''
HootInteractive backend web interface.
'''

import argparse
import os
import pprint
import urllib
import sys
import traceback

import flask
import flask_login
import sqlalchemy

import SecureString

import arao_secret

import controllers.index


LOGGER = arao_secret.conf.get_logger('AraoSecretWeb', None)

APP = flask.Flask(__name__)
APP.secret_key = os.urandom(24)


@APP.before_request
def check_ssl():
    if not APP.debug:
        host_url = urllib.parse.urlparse(flask.request.host_url)
        if host_url.scheme != 'https':
            LOGGER.error('AraoSecret must run over SSL layer !')
            return flask.abort(400)


def get_db():
    '''
    Opens a new database connection if there is none yet for the current application context.
    '''
    if not hasattr(flask.g, 'db_session'):
        flask.g.db_session = arao_secret.db.create_session()
    return flask.g.db_session


@APP.teardown_appcontext
def close_db(error):
    '''
    Close database.
    '''
    if hasattr(flask.g, 'db_session'):
        flask.g.db_session.close()


@APP.errorhandler(500)
def internal_server_error(error):
    '''
    Manage internal server error.
    '''
    alias = None
    if hasattr(flask_login.current_user, 'name'):
        user_name = flask_login.current_user.alias
    msg = '''
URL: {}
Error type: {}
Error: {}

User: {}
IP: {}

Post data:
{}

JSON data:
{}

{}'''.format(flask.request.url, type(error).__name__, str(error),
             user_name, flask.request.remote_addr,
             pprint.pformat(flask.request.form.to_dict()),
             flask.request.get_json(),
             traceback.format_exc())
    LOGGER.error(msg)
    return flask.render_template('500.html', msg=msg), 500


# Login manager extension
LOGIN_MANAGER = flask_login.LoginManager()
LOGIN_MANAGER.init_app(APP)
LOGIN_MANAGER.login_view = 'view_login'

class AnonymousUserMixin(flask_login.AnonymousUserMixin):
    def has_role(self, _):
        return False

LOGIN_MANAGER.anonymous_user = AnonymousUserMixin

class User(flask_login.UserMixin):
    '''
    Proxy for user model.
    '''
    def __init__(self, user):
        self.id = user.id
        self.alias = user.alias

    @classmethod
    def get(cls, user_id):
        '''
        Get User from alias.
        '''
        try:
            return User(get_db().query(arao_secret.db.model.User)
                        .filter(arao_secret.db.model.User.user_id == user_id)
                        .one())
        except sqlalchemy.orm.exc.NoResultFound:
            return None


@LOGIN_MANAGER.user_loader
def load_user(user_id):
    '''
    flask_login requirement.
    callback to reload the user object
    '''
    return User.get(user_id)


def is_safe_url(target):
    '''
    Check if URL is safe, in our domain.
    '''
    ref_url = urllib.parse.urlparse(flask.request.host_url)
    test_url = urllib.parse.urlparse(urllib.parse.urljoin(flask.request.host_url, target))
    return test_url.scheme == 'https' and ref_url.netloc == test_url.netloc


@APP.route('/login', methods=('GET', 'POST'))
def view_login():
    '''
    Authentication function.
    '''
    alias = flask.request.values.get('alias', '')
    password = flask.request.values.get('pass', '')
    if alias and password:
        try:
            # Login and validate the user
            user = arao_secret.manager.get_user(get_db(), alias, password)
            SecureString(password)
            # user should be an instance of your `User` class
            flask_login.login_user(User(user))

            next_ = flask.request.args.get('next')
            # is_safe_url should check if the url is safe for redirects.
            # See http://flask.pocoo.org/snippets/62/ for an example.
            if not is_safe_url(next_):
                return flask.abort(400)

            return flask.redirect(next_ or flask.url_for('view_index'))
        except sqlalchemy.orm.exc.NoResultFound:
            pass
    return flask.render_template('login.html', user=alias)


@APP.route('/logout')
@flask_login.login_required
def view_logout():
    '''
    Simple logout.
    '''
    # Remove the user information from the session
    flask_login.logout_user()
    return flask.redirect(flask.url_for('view_login'))


@APP.route('/')
@flask_login.login_required
def view_index():
    '''
    Main index, entry point.
    '''
    return flask.render_template('login.html', user=alias)


@APP.route('/register', methods=('GET', 'POST'))
def view_register():
    '''
    User registration.
    '''
    alias = ''
    email = ''
    errors = list()
    if flask.request.method == 'POST':
        alias = flask.request.form.get('alias')
        email = flask.request.form.get('email')
        # TODO : Verify password strong
        if flask.request.form.get('password') == flask.request.form.get('password_conf'):
            try:
                user = arao_secret.manager.create_user(get_db(), alias, email,
                                                       flask.request.form.get('password'))
                # user should be an instance of your `User` class
                flask_login.login_user(User(user))
                return flask.redirect(flask.request.args.get('next') or flask.url_for('view_index'))
            except sqlalchemy.exc.IntegrityError:
                errors.append("I'm sorry, your alias is already registered, please,"
                              " choose a different one.")
        else:
            errors.append("I'm sorry, your passwords don't match !'")
    return flask.render_template('register.html', alias=alias, email=email, errors=errors)


def parse_arguments(argv):
    '''
    Arguments parser.
    '''
    parser = argparse.ArgumentParser(description='AraoSecret Web')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='IP to listen for.')
    parser.add_argument('--port', type=int, default=8080, help='Port number to listen for.')
    parser.add_argument('--disable-debug', dest='debug', action='store_false',
                        help='Disable debug mode.')
    parser.set_defaults(debug=True)
    return parser.parse_args(argv[1:])


if __name__ == '__main__':
    ARGS = parse_arguments(sys.argv)
    APP.run(host=ARGS.host, port=ARGS.port, debug=ARGS.debug)
