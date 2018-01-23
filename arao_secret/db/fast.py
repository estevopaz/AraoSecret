'''
HootInteractive MySQL connector.
'''

import datetime
import logging
import MySQLdb

import pandas

import hoot


LOGGER = logging.getLogger(__name__)


def commit(connection, close=True):
    '''
    Commit connection changes.
    '''
    conn, _ = connection
    try:
        conn.commit()
    except Exception as error:
        msg = '{}: {}\nSkipping query, rollback !'.format(type(error).__name__, str(error))
        LOGGER.error(msg)
        conn.rollback()
        raise error
    if close:
        conn.close()


def connect():
    '''
    Create database connection.
    '''
    conn = MySQLdb.connect(host=hoot.conf.get('DB', 'host'),
                           port=int(hoot.conf.get('DB', 'port')),
                           user=hoot.conf.get('DB', 'user'),
                           passwd=hoot.conf.get('DB', 'pass'),
                           db=hoot.conf.get('DB', 'db'),
                           use_unicode=True, charset='utf8',
                           sql_mode='TRADITIONAL')
    conn.autocommit(False)
    return conn, conn.cursor(MySQLdb.cursors.DictCursor)


def execute(sql, values, connection=None):
    '''
    Execute insertions/deletions query for many or single rows.
    '''
    try:
        if connection:
            auto_connection = False
            conn, cursor = connection
        else:
            auto_connection = True
            conn, cursor = connect()
        if len(values) > 0 and isinstance(values[0], (list, tuple)):
            cursor.executemany(sql, values)
        else:
            cursor.execute(sql, values)
        if auto_connection:
            conn.commit()
    except Exception as error:
        if len(values) > 3 and isinstance(values[0], (list, tuple)):
            msg = ('{}: {}\nSkipping query, rollback !\nQuery: {}\nParams: {} ...'
                   .format(type(error).__name__, str(error), sql, values[:3]))
        else:
            msg = ('{}: {}\nSkipping query, rollback !\nQuery: {}\nParams: {}'
                   .format(type(error).__name__, str(error), sql, values))
        LOGGER.error(msg)
        if auto_connection:
            conn.rollback()
            conn.close()
        raise error


def query(sql, params=None, connection=None, dataframe=False):
    '''
    Execute query.

    Parameters
    ----------
    conn : DataBase connection.
    sql : string, query to execute.
    fetch_all : boolean (True), store all by default.

    Returns
    -------
    result : query results.
    '''
    if connection:
        auto_connection = False
        conn, cursor = connection
    else:
        auto_connection = True
        conn, cursor = connect()
    if params:
        try:
            cursor.execute(sql, params)
        except TypeError as error:
            msg = ('{}: {}\nSkipping query, rollback !\nQuery: {}\nParams: {}'
                   .format(type(error).__name__, str(error), sql, params))
            LOGGER.error(msg)
            raise error
    else:
        cursor.execute(sql)
    data = cursor.fetchall()
    if auto_connection:
        conn.close()
    if dataframe:
        data = pandas.DataFrame(list(data))
    return data


def replacements():
    '''
    Get URL replacements for correct split.
    '''
    return query('''SELECT type, find, `replace` FROM libr_find_replace''')


def ad_group_status_diff(advertiser_id, date=None, only_changes=True):
    '''
    Get AdGroups which current status must be updated.
    '''
    if not date:
        date = datetime.date.today()
    # Filter N/A Status, which can come from AdGroupStatusFromSitemap
    if only_changes:

        # Get changes
        df_changes = (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                      .select({'Status': 'distinct'})
                      .where(['date = "{}"'.format(date),
                              '(AdGroup Status = "PAUSED" and Status = "good url")'
                              ' or (AdGroup Status = "ENABLED" and Status = "no inventory")'])
                      .group_by(['Campaign ID', 'AdGroup ID', 'AdGroup Status'])
                      .read())
        # Get AdGroups with conflicting status for their Final URLs
        df_conf_status = (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                          .select({'Status': 'distinct'})
                          .where(['date = "{}"'.format(date),
                                  'Status = "good url" or Status = "no inventory"'])
                          .group_by(['Campaign ID', 'AdGroup ID', 'AdGroup Status'])
                          .read())
        df_conf_status = df_conf_status[df_conf_status['Status'].apply(len) > 1]
        df_res = df_changes.join(df_conf_status, rsuffix=' conflicting')

    else:

        df_res = (hoot.db.anadb.DB(advertiser_id).Table('AdWords')
                  .select({'Status': 'distinct'})
                  .where(['date = "{}"'.format(date),
                          'Status = "good url" or Status = "no inventory"'])
                  .group_by(['Campaign ID', 'AdGroup ID', 'AdGroup Status'])
                  .read())
        df_res['Status conflicting'] = df_res['Status']

    # Exclude "Not available" status
    df_res = df_res[df_res['Status'] != 'N/A']

    # Set PAUSED and "Good URL" to ENABLED
    df_res.loc[df_res['Status'] == ('good url',), 'Status'] = 'ENABLED'
    # Set ENABLED and "No inventory" to PAUSED
    df_res.loc[df_res['Status'] == ('no inventory',), 'Status'] = 'PAUSED'

    # Conflictive status, "Good URL" and "No inventory" at same in the AdGroup
    df_res['Status conflicting'] = df_res['Status conflicting'].isin((('good url', 'no inventory'),
                                                                      ('no inventory', 'good url')))
    df_res.loc[df_res['Status conflicting'] == True, 'Status'] = None
    # Set PAUSE when conflictive and ENABLED
    df_res.reset_index('AdGroup Status', inplace=True)
    mask = (df_res['Status conflicting'] == True) & (df_res['AdGroup Status'] == 'ENABLED')
    df_res.loc[mask, 'Status'] = 'PAUSED'

    # Remove AdGroup Status to prevent append it again
    del df_res['AdGroup Status']

    df_res.rename(columns={'Status': 'AdGroup status change'}, inplace=True)
    return df_res


def sitemap_client(client):
    '''
    Get Sitemap data from client, for every advertiser of it.
    '''
    # Set columns to empty DataFrame
    df_result = pandas.DataFrame({'Dealer ID': [], 'Condition': [], 'VIN': []})
    for advertiser in client.advertisers:
        try:
            df_adv = (hoot.db.anadb.DB(advertiser.id_).Table('Sitemap')
                      .select(['Condition', 'VIN'])
                      .where(['date = "{}"'.format(datetime.date.today()),
                              'VIN is not null',
                              'Condition is not null'])
                      .read())
        except hoot.db.anadb.AnaDBError as error:
            LOGGER.error('%s : %s', advertiser.id_, str(error))
            if error.code in (1, 5):
                continue
        df_adv['Dealer ID'] = advertiser.nickname
        df_result = df_result.append(df_adv)

    # Add data from VIN API
    hoot.vin.append(df_result, ('Make', 'Model', 'Year'))

    # Filter records with any null value
    df_result = hoot.save.filter_nulls(df_result)

    # Allow empty trim
    hoot.vin.append(df_result, ('Trim', ))

    df_result.rename(columns={'Condition': 'Type'}, inplace=True)
    df_result.sort_values(['Dealer ID', 'Make', 'Model', 'Trim', 'Year', 'Type', 'VIN'],
                          inplace=True)
    return df_result[['Dealer ID', 'Make', 'Model', 'Trim', 'Year', 'Type', 'VIN']]


def sitemap_all(advertiser_id):
    '''
    Get sitemap data to CSV.
    '''
    try:
        return (hoot.db.anadb.DB(advertiser_id).Table('Sitemap')
                .where('date = "{}"'.format(datetime.date.today()))
                .read())
    except hoot.db.anadb.AnaDBError as error:
        return pandas.DataFrame({'Error': [str(error)]})


def sitemap_update(advertiser_id, df_results):
    '''
    Database update with sitemap results.
    '''
    connection = connect()

    # Remove previous URLs to be insert
    sql = '''DELETE FROM proc_parse_sitemap
             WHERE advertiser_id = %s'''
    execute(sql, (advertiser_id, ), connection)

    # Insertions
    if not df_results.empty:
        sql = '''INSERT INTO proc_parse_sitemap
                 (recdate, advertiser_id, url, vehicle_condition, make, model, year, price, vin,
                  title, img_url, img_url_2, description)
                 VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        params = list()
        for _, series in df_results.iterrows():
            row = dict()
            # Drop NaN values
            series[series.isnull()] = None
            # Get data when available
            for attribute in ('Condition', 'Description', 'Image URL', 'Image URL #2', 'Price',
                              'Title', 'URL', 'VIN'):
                if attribute in series:
                    row[attribute] = series[attribute]
                else:
                    row[attribute] = None
            # Add row
            params.append(
                (advertiser_id, row['URL'], row['Condition'],
                 hoot.vin.get_data(row['VIN'], key='Make'),
                 hoot.vin.get_data(row['VIN'], key='Model'),
                 hoot.vin.get_data(row['VIN'], key='Year', data_type=int),
                 row['Price'], row['VIN'], row['Title'], row['Image URL'], row['Image URL #2'],
                 row['Description'])
            )
        execute(sql, params, connection)

    commit(connection)

    msg = '{} : Sitemap scrapping data saved.'.format(advertiser_id)
    LOGGER.info(msg)


def xpaths(advertiser_id):
    '''
    Get XPaths for given account.
    '''
    sql = '''
        SELECT *
        FROM cdata_scrape_xpath
        WHERE advertiser_id = %s
    '''
    return query(sql, (advertiser_id, ))
