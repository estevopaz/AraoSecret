'''
Common functions for controllers.
'''

import datetime
import io
import json
import os

import flask
import pandas

import hoot


def anadb_data(advertiser_id, source, date=None, null_to_empty=True):
    '''
    Get AdWords data from concrete date, today as default.
    '''
    if not date:
        date = datetime.date.today()
    try:
        dataframe = (hoot.db.anadb.DB(advertiser_id).Table(source)
                     .where('date = "{}"'.format(date))
                     .read())
        if null_to_empty:
            dataframe.fillna(value='', inplace=True)
    except hoot.db.anadb.AnaDBError as error:
        return pandas.DataFrame({'Error': [error.message]}, ['Error'])
    if dataframe.empty:
        return pandas.DataFrame({'Warning': ['Empty {} data !'.format(source)]}, ['Warning'])
    return dataframe


def get_dataset(advertiser_id, source, columns=None, date=None):
    '''
    Get data from AnaDB and transform it to be used for DataTables JS lib.
    '''
    dataframe = anadb_data(advertiser_id, source, date)
    if columns:
        columns_present = list()
        for column in columns:
            if column in dataframe:
                columns_present.append(column)
        for column in ('Error', 'Warning'):
            if column in dataframe:
                columns_present.append(column)
    else:
        columns_present = dataframe.columns.tolist()
    dataframe = dataframe[columns_present]
    return {'columns': columns_present, 'data': json.dumps(dataframe.to_dict('split')['data'])}


def _count_value(series, value):
    '''
    Get number of occurrences of given value.
    '''
    values = series.value_counts()
    if value not in values:
        return 0
    return values[value]


def adwords_statistics(advertiser):
    '''
    Get Inventory Checker statistics from today.
    '''
    if not advertiser.statistics:
        return None

    data = {
        'Key': [
            'Ad Groups', 'Enabled', 'Paused', 'Changed'
        ],
        'Value': [
            advertiser.statistics.adgroups,
            advertiser.statistics.adgroups_enabled,
            advertiser.statistics.adgroups_paused,
            advertiser.statistics.changed_adgroup_statuses
        ],
        '_color_': 'black'
    }
    dataframe = pandas.DataFrame(data)
    dataframe.set_index('Key', inplace=True)

    if dataframe.ix['Ad Groups']['Value'] == 0:
        dataframe.loc['Ad Groups', '_color_'] = 'red'
    if dataframe.ix['Enabled']['Value'] == 0:
        dataframe.loc['Enabled', '_color_'] = 'red'
    if dataframe.ix['Paused']['Value'] == 0:
        dataframe.loc['Paused', '_color_'] = 'red'
    if dataframe.ix['Changed']['Value'] / dataframe.ix['Ad Groups']['Value'] > 0.5:
        dataframe.loc['Changed', '_color_'] = 'red'

    return dataframe


def ichecker_statistics(advertiser_id):
    '''
    Get Inventory Checker statistics from today.
    '''
    dataframe = anadb_data(advertiser_id, 'AdWords')
    if 'Error' in dataframe or 'Warning' in dataframe:
        return dataframe

    if 'Status' not in dataframe:
        return pandas.DataFrame({'Warning': ['No iChecker executed today !']}, ['Warning'])

    # Create data
    data = {
        'Key': [
            'URLs', 'Duplicated', 'Good', 'No inventory', 'Errors'
        ],
        'Value': [
            len(dataframe),
            _count_value(dataframe['Final URL'].duplicated(), True),
            _count_value(dataframe['Status'], 'good url'),
            _count_value(dataframe['Status'], 'no inventory'),
            (len(dataframe) - _count_value(dataframe['HTTP Code'], '200 OK')
             - _count_value(dataframe['HTTP Code'], 'N/A'))
        ],
        '_color_': 'black'
    }
    dataframe = pandas.DataFrame(data)
    dataframe.set_index('Key', inplace=True)

    # Set colours
    # Duplicated
    if dataframe.ix['Duplicated']['Value'] + 1 == dataframe.ix['URLs']['Value']:
        dataframe.loc['Duplicated', '_color_'] = 'red'
    # Good URLs
    if dataframe.ix['Good']['Value'] in (0, dataframe.ix['URLs']['Value']):
        dataframe.loc['Good', '_color_'] = 'red'
    elif dataframe.ix['Good']['Value'] > dataframe.ix['No inventory']['Value']:
        dataframe.loc['Good', '_color_'] = 'orange'
    else:
        dataframe.loc['Good', '_color_'] = 'green'
    # No inventory
    if dataframe.ix['No inventory']['Value'] in (0, dataframe.ix['URLs']['Value']):
        dataframe.loc['No inventory', '_color_'] = 'red'
    elif dataframe.ix['No inventory']['Value'] < dataframe.ix['Good']['Value']:
        dataframe.loc['No inventory', '_color_'] = 'orange'
    else:
        dataframe.loc['No inventory', '_color_'] = 'green'
    # Errors
    if dataframe.ix['Errors']['Value'] > 0:
        dataframe.loc['Errors', '_color_'] = 'red'
    else:
        dataframe.loc['Errors', '_color_'] = 'green'

    return dataframe


def icounter_statistics(advertiser_id):
    '''
    Get Inventory Counter statistics from today.
    '''
    dataframe = anadb_data(advertiser_id, 'AdWords', null_to_empty=False)
    if 'Error' in dataframe or 'Warning' in dataframe:
        return dataframe

    if 'Status' not in dataframe:
        return pandas.DataFrame({'Warning': ['No iChecker executed today !']}, ['Warning'])
    if 'Count' not in dataframe:
        return pandas.DataFrame({'Warning': ['No iCounter executed today !']}, ['Warning'])

    # Create data
    data = {
        'Key': [
            'URLs', 'Checked', 'No count', 'No price'
        ],
        'Value': [
            _count_value(dataframe['Status'], 'good url'),
            _count_value(dataframe['Count'].notnull(), True),
            _count_value(dataframe['Count'], 0),
            _count_value(dataframe['Price min.'], 0)
        ],
        '_color_': 'black'
    }
    dataframe = pandas.DataFrame(data)
    dataframe.set_index('Key', inplace=True)

    # Set colours
    # Checked URLs
    if dataframe.ix['Checked']['Value'] == dataframe.ix['URLs']['Value']:
        dataframe.loc['Checked', '_color_'] = 'green'
    else:
        dataframe.loc['Checked', '_color_'] = 'red'
    # No count
    if dataframe.ix['No count']['Value'] == dataframe.ix['Checked']['Value']:
        dataframe.loc['No count', '_color_'] = 'red'
    elif dataframe.ix['No count']['Value'] > 0:
        dataframe.loc['No count', '_color_'] = 'orange'
    else:
        dataframe.loc['No count', '_color_'] = 'green'
    # No price
    if dataframe.ix['No price']['Value'] == dataframe.ix['Checked']['Value']:
        dataframe.loc['No price', '_color_'] = 'red'
    elif dataframe.ix['No price']['Value'] > 0:
        dataframe.loc['No price', '_color_'] = 'orange'
    else:
        dataframe.loc['No price', '_color_'] = 'green'

    return dataframe


def sitemap_statistics(advertiser_id):
    '''
    Get Sitemap statistics from today.
    '''
    dataframe = anadb_data(advertiser_id, 'Sitemap', null_to_empty=False)
    if 'Error' in dataframe or 'Warning' in dataframe:
        return dataframe

    csv_path = os.path.join(hoot.conf.reports_path(advertiser_id),
                            'adwords_dynamic_remarketing_feed.csv')
    if os.path.exists(csv_path):
        csv_data = pandas.read_csv(csv_path)
        csv_length = len(csv_data)
    else:
        csv_data = pandas.DataFrame({'Warning': ['No CSV exported !']})
        csv_length = 0

    # Create data
    data = {
        'Key': [
            'URLs', 'No VIN', 'No price', 'No image', 'AdWords Dyn. Remark.'
        ],
        'Value': [
            len(dataframe),
            _count_value(dataframe['VIN'].isnull(), True),
            _count_value(dataframe['Price'].isnull(), True),
            _count_value(dataframe['Image URL'].isnull(), True),
            csv_length
        ],
        '_color_': 'black'
    }
    dataframe = pandas.DataFrame(data)
    dataframe.set_index('Key', inplace=True)

    # Set colours
    # URLs
    if dataframe.ix['URLs']['Value'] == 0:
        dataframe.loc['Checked', '_color_'] = 'red'
    # No VIN
    if dataframe.ix['No VIN']['Value'] == 0:
        dataframe.loc['No VIN', '_color_'] = 'green'
    else:
        dataframe.loc['No VIN', '_color_'] = 'red'
    # No price
    if dataframe.ix['No price']['Value'] == dataframe.ix['URLs']['Value']:
        dataframe.loc['No price', '_color_'] = 'red'
    elif dataframe.ix['No price']['Value'] > 0:
        dataframe.loc['No price', '_color_'] = 'orange'
    else:
        dataframe.loc['No price', '_color_'] = 'green'
    # AdWords Dyn. Remark.
    if dataframe.ix['AdWords Dyn. Remark.']['Value'] == dataframe.ix['URLs']['Value']:
        dataframe.loc['AdWords Dyn. Remark.', '_color_'] = 'green'
    elif dataframe.ix['AdWords Dyn. Remark.']['Value'] == 0:
        dataframe.loc['AdWords Dyn. Remark.', '_color_'] = 'red'

    return dataframe
