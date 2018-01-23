'''
Events controller.
'''

import datetime

import flask

import hoot


def main(db_session):
    '''
    Events list.
    '''
    initial_date = datetime.datetime.now() - datetime.timedelta(days=60)
    events = (db_session.query(hoot.db.model.Event)
              .filter(hoot.db.model.Event.created >= initial_date)
              .all())
    return flask.render_template('events.html', events=events)
