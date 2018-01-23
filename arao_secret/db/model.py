'''
DataBase models for AraoSecret.
'''

# Allow id as attribute for database models
# pylint: disable=C0103
# Avoid warning for few methods
# pylint: disable=R0903


import logging

import SecureString

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy.orm import relationship

import arao_secret
from arao_secret.db import BASE


LOGGER = logging.getLogger(__name__)


class User(BASE):
    '''
    AraoSecret user.
    '''
    __tablename__ = 'user'

    id = Column('id', Integer, primary_key=True)
    alias = Column(String(32), nullable=False, unique=True)
    email = Column(String(128), nullable=False)
    email_validated = Column(Boolean, default=False)
    pass_hash = Column(LargeBinary(64), nullable=False)
    rsa_key = Column(LargeBinary(3310), nullable=False)
    rsa_key_pub = Column(LargeBinary(799), nullable=False)

    def __init__(self, alias, email, password):
        self.alias = alias
        self.email = email
        self.pass_hash = arao_secret.helper.get_pass_hash(password)
        # RSA
        rsa_key = RSA.generate(4096)
        self.rsa_key = rsa_key.exportKey(passphrase=password)
        self.rsa_key_pub = rsa_key.publickey().exportKey()
        # TODO : Clean rsa_key from memory

    def __repr__(self):
        return '{}, {}'.format(self.id, self.alias)

    def decrypt(self, password, text_enc):
        rsa_key = RSA.importKey(self.rsa_key, passphrase=password)
        text = rsa_key.decrypt(text_enc)
        # TODO : Clean rsa_key from memory
        return text

    def encrypt(self, text):
        rsa_key = RSA.importKey(self.rsa_key_pub)
        text_enc = rsa_key.encrypt(text, None)[0]
        SecureString.clearmem(text)
        return text_enc

    def get_group(self, id):
        '''
        Get Group, Group key tuple.
        '''
        for group_key in self.group_keys:
            if group_key.group.id == id:
                return group_key.group, group_key
        return None

    def get_groups(self):
        groups = list()
        for group_key in self.group_keys:
            groups.append(group_key.group)
        # TODO : Sort by name
        return groups


class Group(BASE):
    '''
    AraoSecret group.
    '''
    __tablename__ = 'group'

    id = Column(Integer, primary_key=True)
    aes_iv = Column(LargeBinary(16), nullable=False)

    def __init__(self):
        self.aes_iv = Random.new().read(AES.block_size)

    def __repr__(self):
        return str(self.id)


class UserGroupKey(BASE):
    '''
    Association between users and groups.

    All data except IDs is encrypted.

    TODO : If user removed from group, all group data must be re-encrypted.
           If he has DB access and save the group key, he can access to future secrets of group.
    '''
    __tablename__ = 'user_group_key'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    group_name = Column(LargeBinary(512), nullable=False)
    group_key = Column(LargeBinary(512), nullable=False)

    user = relationship(User, backref='group_keys')
    group = relationship(Group, backref='group_keys')

    # Cache
    _cache_ = dict()

    def __init__(self, user, group, group_name, group_key):
        self.user_id = user.id
        self.group_id = group.id
        self.group_name = user.encrypt(group_name)
        self.group_key = user.encrypt(group_key)
        self.user = user
        self.group = group

    def __repr__(self):
        return '{} -> {}'.format(self.user, self.group)

    def clear(self):
        '''
        Clean object info in memory.
        '''
        for key in self._cache_:
            if not isinstance(self._cache_[key], int):
                SecureString.clearmem(self._cache_[key])

    def decrypt(self, user_pass, text_enc):
        '''
        Decrypt with group key.
        '''
        group_key = self.user.decrypt(user_pass, self.group_key)
        key = AES.new(group_key, AES.MODE_CBC, self.group.aes_iv)
        text = arao_secret.helper.from_bytes(key.decrypt(text_enc))
        # Memory clean
        # TODO : Clean key from memory
        SecureString.clearmem(group_key)
        return text

    def encrypt(self, user_pass, text):
        '''
        Encrypt with group key.
        '''
        text_bytes = arao_secret.helper.to_bytes(text)
        group_key = self.user.decrypt(user_pass, self.group_key)
        key = AES.new(group_key, AES.MODE_CBC, self.group.aes_iv)
        text_enc = key.encrypt(text_bytes)
        # Memory clean
        # TODO : Clean key from memory
        SecureString.clearmem(group_key)
        SecureString.clearmem(text_bytes)
        return text_enc

    def get_clear(self, user_pass):
        '''
        Get clear info from object.
        Note: After use it, call to self.clear()
        '''
        self._cache_['group_id'] = self.group_id
        self._cache_['group_name'] = arao_secret.helper.from_bytes(
            self.user.decrypt(user_pass, self.group_name)
        )
        return self._cache_

    def update(self, group_name):
        '''
        Update object attributes.
        '''
        self.group_name = self.user.encrypt(group_name)
        # Memory clean
        SecureString.clearmem(group_name)


class Secret(BASE):
    '''
    Secret data

    All data except IDs is encrypted.
    '''
    __tablename__ = 'secret'

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    name = Column(LargeBinary(256), nullable=False)
    url = Column(LargeBinary(512), nullable=False)
    login = Column(LargeBinary(256), nullable=False)
    password = Column(LargeBinary(512), nullable=False)
    comment = Column(LargeBinary(4096))

    group = relationship(Group, backref='secrets')

    # Cache
    _cache_ = dict()

    def __init__(self, user_pass, user_group_key, name, url, login, password, comment):
        self.group_id = user_group_key.group.id
        self.name = user_group_key.encrypt(user_pass, name)
        self.url = user_group_key.encrypt(user_pass, url)
        self.login = user_group_key.encrypt(user_pass, login)
        self.password = user_group_key.encrypt(user_pass, password)
        self.comment = user_group_key.encrypt(user_pass, comment)
        self.group = user_group_key.group

    def __repr__(self):
        return self.id

    def clear(self):
        '''
        Clean object info in memory.
        '''
        for key in self._cache_:
            if not isinstance(self._cache_[key], int):
                SecureString.clearmem(self._cache_[key])

    def get_clear(self, user_pass, user_group_key, attribute=None):
        '''
        Get clear info from object.
        Note: After use it, call to self.clear()
        '''
        if attribute:
            LOGGER.info('User %i reading %s from secret %i',
                        user_group_key.user.id, attribute, self.id)
            if attribute.endswith('id'):
                self._cache_[attribute] = eval('self.' + attribute)
            else:
                self._cache_[attribute] = user_group_key.decrypt(user_pass,
                                                                 eval('self.' + attribute))
        else:
            LOGGER.info('User %i reading all from secret %i', user_group_key.user.id, self.id)
            self._cache_['id'] = self.id
            self._cache_['group_id'] = self.group_id
            self._cache_['name'] = user_group_key.decrypt(user_pass, self.name)
            self._cache_['url'] = user_group_key.decrypt(user_pass, self.url)
            self._cache_['login'] = user_group_key.decrypt(user_pass, self.login)
            self._cache_['password'] = user_group_key.decrypt(user_pass, self.password)
            self._cache_['comment'] = user_group_key.decrypt(user_pass, self.comment)
        return self._cache_

    def update(self, user_pass, user_group_key, name, url, login, password, comment):
        '''
        Update object attributes.
        '''
        self.name = user_group_key.encrypt(user_pass, name)
        self.url = user_group_key.encrypt(user_pass, url)
        self.login = user_group_key.encrypt(user_pass, login)
        self.password = user_group_key.encrypt(user_pass, password)
        self.comment = user_group_key.encrypt(user_pass, comment)
        for string in (name, url, login, password, comment):
            SecureString.clearmem(string)
