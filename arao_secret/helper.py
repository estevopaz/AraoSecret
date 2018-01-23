'''
Common functions.
'''

import hashlib

from Crypto.Cipher import AES
from Crypto import Random
import SecureString

import arao_secret


# Stupid trick to prevent pylint warning
hashlib.sha3_512 = hashlib.sha3_512
SecureString.clearmem = SecureString.clearmem


def aes_iv_gen():
    '''
    Generate IV for AES CBC.
    '''
    return Random.new().read(AES.block_size)


def aes_key_gen():
    '''
    Generate key for AES.
    '''
    return Random.new().read(32)


def cleaned(text):
    '''
    Check if string was cleaned in memory.
    '''
    if text == b'\x00' * len(text):
        return True
    return False


def decrypt_from_session(pass_enc):
    '''
    Decrypt password from memory by session key.
    '''
    key = AES.new(arao_secret.APP_KEY['aes_key'], AES.MODE_CBC, arao_secret.APP_KEY['aes_iv'])
    # TODO : Clear key
    return key.decrypt(pass_enc)


def encrypt_for_session(password):
    '''
    Encrypt password into memory by session key.
    '''
    key = AES.new(arao_secret.APP_KEY['aes_key'], AES.MODE_CBC, arao_secret.APP_KEY['aes_iv'])
    pass_fill = fill_out_to_mod_16(password)
    pass_enc = key.encrypt(password)
    # TODO : Clear key
    SecureString.clearmem(password)
    return pass_enc


def fill_out_to_mod_16(text):
    '''
    Fill out text to fill mod 16.
    '''
    mod = len(text) % 16
    if mod:
        res = text + b'\x00' * (16 - mod)
        # Clear memory of previous object
        SecureString.clearmem(text)
    else:
        res = text
    return res


def fill_out_undo(text):
    '''
    Undo text fill out.
    '''
    text_strip = text.rstrip(b'\x00')
    if id(text) != id(text_strip):
        # Clear memory of previous object
        SecureString.clearmem(text)
    return text_strip


def from_bytes(text):
    '''
    Get string from bytes.
    '''
    text = fill_out_undo(text)
    text_decoded = text.decode(arao_secret.ENCODING)
    # Clear memory of previous object
    SecureString.clearmem(text)
    return text_decoded


def get_pass_hash(password):
    '''
    Get hash from password.
    '''
    return hashlib.sha3_512(password).digest()


def to_bytes(text):
    '''
    Convert string to bytes.
    '''
    if isinstance(text, bytes):
        text_encoded = text
    else:
        text_encoded = text.encode(arao_secret.ENCODING)
        # Clear memory of previous object
        SecureString.clearmem(text)
    return fill_out_to_mod_16(text_encoded)
