'''
Index view controller.
'''

import flask


def view(db_session):
    '''
    Main view.
    '''
    return flask.render_template('index.html')
