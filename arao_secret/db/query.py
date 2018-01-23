'''
Common queries helper.
'''

import datetime
import logging

import sqlalchemy

import hoot


LOGGER = logging.getLogger(__name__)

CHAR_REPLACES = {'%20', ' ', '_', '-', '+', '', '--', '~'}


def advertiser(db_session, advertiser_id):
    '''
    Get advertiser object.
    '''
    return (db_session.query(hoot.db.model.Advertiser)
            .filter(hoot.db.model.Advertiser.id_ == advertiser_id)
            .one())


def advertiser_adwords_map(db_session):
    '''
    Get all active advertiser IDs.
    '''
    ids = dict()
    for advertiser_id, account_id in (db_session.query(hoot.db.model.Advertiser.id_,
                                                       hoot.db.model.Advertiser.googleid)
                                      .filter(hoot.db.model.Advertiser.active == True)
                                      .all()):
        ids[advertiser_id] = account_id
    return ids


def advertisers(db_session, active=True, client_id=None):
    '''
    Get advertiser object.
    '''
    query = db_session.query(hoot.db.model.Advertiser)
    if active:
        query = query.filter(hoot.db.model.Advertiser.active == True)
    if client_id:
        query = query.filter(hoot.db.model.Advertiser.clientid == client_id)
    return (query.order_by(hoot.db.model.Advertiser.active.desc(),
                           hoot.db.model.Advertiser.id_)
            .all())


def client(db_session, client_id):
    '''
    Get client.
    '''
    return db_session.query(hoot.db.model.Client).filter(hoot.db.model.Client.id == client_id).one()


def clients(db_session, active=True):
    '''
    Get clients.
    '''
    query = db_session.query(hoot.db.model.Client)
    if active:
        query = query.filter(hoot.db.model.Client.active == True)
    return query.all()


def crawler_srp(db_session, crawler_name_or_id):
    '''
    Get SRP crawler configuration.
    '''
    query = db_session.query(hoot.db.model.CrawlerSRP)
    if crawler_name_or_id.isdecimal():
        query = query.filter(hoot.db.model.CrawlerSRP.id_ == int(crawler_name_or_id))
    else:
        query = query.filter(hoot.db.model.CrawlerSRP.name == crawler_name_or_id)
    return query.one()


def crawler_srp_result(db_session, url):
    '''
    Get SRP result crawler by URL.
    '''
    try:
        return (db_session.query(hoot.db.model.CrawlerSRPResults)
                .filter(hoot.db.model.CrawlerSRPResults.url == url).one())
    except sqlalchemy.orm.exc.NoResultFound:
        return None


def makes(db_session):
    '''
    Get list of makes with their alias.
    '''
    res = dict()
    for make, in (db_session.query(hoot.db.model.MakeModel.make)
                  .filter(hoot.db.model.MakeModel.client_id == -1)
                  .distinct()
                  .all()):
        res[make] = list()
        res[make].append(make.lower())
        for string in ('-', ' ', ' & ', ' and '):
            if string in make:
                for replace in CHAR_REPLACES.difference({string}):
                    res[make].append(make.replace(string, replace).lower())
    # Add short by length for makes
    res['_order_'] = sorted(res.keys(), key=len, reverse=True)
    return res


def models(db_session):
    '''
    Get list of models as list of strings from longer to shorter.
    '''
    res = dict()
    for model in (db_session.query(hoot.db.model.MakeModel)
                  .filter(hoot.db.model.MakeModel.client_id == -1)
                  .all()):
        if model.make not in res:
            res[model.make] = dict()
        res[model.make][model.model] = list()
        res[model.make][model.model].append(model.model.lower())
        for string in ('-', ' ', ' & ', ' and '):
            if string in model.model:
                for replace in CHAR_REPLACES.difference({string}):
                    res[model.make][model.model].append(
                        model.model.replace(string, replace).lower())
    # Add short by length for models
    for make in res:
        res[make]['_order_'] = sorted(res[make].keys(), key=len, reverse=True)
    return res


def user(db_session, user_id=None, alias=None, password=None):
    '''
    Get user.
    '''
    query = db_session.query(hoot.db.model.User)
    if user_id:
        query = query.filter(hoot.db.model.User.id_ == user_id)
    if alias:
        query = query.filter(hoot.db.model.User.alias == alias)
    if password:
        query = query.filter(hoot.db.model.User.password == password)
    return query.one()


def vin(db_session, _vin_):
    '''
    Get VIN data from database, None if not present.
    '''
    try:
        return db_session.query(hoot.db.model.VIN).filter(hoot.db.model.VIN.vin == _vin_).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return None
