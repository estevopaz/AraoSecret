'''
Client controller.
'''

import flask
import flask_login

import hoot

import controllers.advertiser

def main(db_session, client_id):
    '''
    Advertiser main panel.
    '''
    advertisers_table = controllers.advertiser.get_datatable(
        db_session.query(hoot.db.model.Advertiser)
        .filter(hoot.db.model.Advertiser.clientid == client_id)
        .all()
    )
    return flask.render_template(
        'client.html',
        advertisers=hoot.db.query.advertisers(db_session),
        client=hoot.db.query.client(db_session, client_id),
        advertisers_table=advertisers_table
    )
