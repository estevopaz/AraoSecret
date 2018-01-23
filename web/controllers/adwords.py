# -*- coding: utf-8 -*-
"""
This Blueprint handles the registration flow, including oauth.
No Login Tool authentication is required in any of these views.
"""

import logging
import oauth2client

import flask

import hoot


LOGGER = logging.getLogger(__name__)


def authorization(client_id):
    '''
    Redirect the user to the Google OAuth page to grant us access to his AdWords data.
    '''
    flow = hoot.adwords.authorization.get_flow(
        redirect_uri=flask.url_for('view_oauth2callback', _external=True),
        state='client_{}'.format(client_id))
    auth_uri = flow.step1_get_authorize_url()
    return flask.make_response(flask.redirect(auth_uri))


def oauth2callback(db_session):
    '''
    Manage AdWords OAuth2 callback.
    '''
    if 'code' in flask.request.args:
        try:
            flow = hoot.adwords.authorization.get_flow(
                redirect_uri=flask.url_for('view_oauth2callback', _external=True))
            credentials = flow.step2_exchange(flask.request.args['code'])
        except oauth2client.client.FlowExchangeError as error:
            LOGGER.error('Failed communication with Google OAuth2 service.')
            raise RuntimeError("Failed communication with Google's authentication service.")

        # Save refresh token for client
        client_id = int(flask.request.args['state'].split('_')[1])
        client = db_session.query(hoot.db.model.Client).filter(hoot.db.model.Client.id == client_id).one()
        client.refresh_token = credentials.refresh_token
        db_session.commit()

    else:
        # If error not in request.args, an exception is raised that
        # automatically returns BadRequestKeyError: 400: Bad Request
        # Usually "access_denied"
        raise RuntimeError('Error from AdWords ({})'.format(flask.request.args['error']))

    return flask.redirect(flask.url_for('view_client', client_id=1))  # TODO
