'''
Data Base connection.
'''

from sqlalchemy.ext.declarative import declarative_base as _declarative_base
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import scoped_session as _scoped_session
from sqlalchemy.orm import sessionmaker as _sessionmaker

from arao_secret import conf


def create_session(autocommit=False, autoflush=False, pool_recycle=3600):
    '''
    Create a new MySQL/PostgreSQL session.

    Parameters
    ----------
    autocommit : Boolean (False), see sqlalchemy documentation.
    autoflush : Boolean (False), see sqlalchemy documentation.
    pool_recycle : Integer (7200), causes the pool to recycle connections
                   after the given number of seconds has passed.

    Returns
    -------
    session : Database session.
    '''
    engine = _create_engine(conf.get('DB', 'URI'),
                            convert_unicode=True,
                            pool_recycle=pool_recycle)
    session = _scoped_session(_sessionmaker(autocommit=autocommit,
                                            autoflush=autoflush,
                                            bind=engine))

    # The following dumb assignments on session are just to trick pylint
    # so that it doesn't report "missing attribute" every time the session is used
    session.add = session.add
    session.commit = session.commit
    session.delete = session.delete
    session.flush = session.flush
    session.get_bind = session.get_bind
    session.query = session.query
    session.refresh = session.refresh
    session.rollback = session.rollback

    return session


BASE = _declarative_base()
from arao_secret.db import model


def create_tables(db_session):
    '''
    Create tables into existent DataBase.
    '''
    BASE.metadata.create_all(db_session.bind)
