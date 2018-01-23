'''

Usage example:

    import arao_secret

    db_session = arao_secret.db.create_session()
    arao_secret.db.create_tables(db_session)

    user = arao_secret.manager.create_user(db_session, 'alias_test', 'email_test', 'pass_test')
    group, user_group_key = user.create_group(db_session, 'group_test')
    secret = user.create_secret(db_session, group, 'name_test', 'url_test', 'login_test',
                                'password_test', 'comment_test')

'''

import SecureString

import arao_secret


def create_user(db_session, alias, email, password):
    pass_bytes = arao_secret.helper.to_bytes(password)
    SecureString.clearmem(password)
    user = arao_secret.db.model.User(alias, email, pass_bytes)
    db_session.add(user)
    db_session.commit()
    return get_user(db_session, alias, pass_bytes)


def get_user(db_session, alias, password):
    pass_bytes = arao_secret.helper.to_bytes(password)
    user = (db_session.query(arao_secret.db.model.User)
            .filter(arao_secret.db.model.User.alias == alias)
            .filter(arao_secret.db.model.User.pass_hash
                    == arao_secret.helper.get_pass_hash(pass_bytes))
            .one())
    return UserManager(user, pass_bytes)


class UserManager:
    '''
    User manager.
    '''
    def __init__(self, user, password):
        self.user = user
        self.password = arao_secret.helper.encrypt_for_session(password)
        if not arao_secret.helper.cleaned(password):
            raise RuntimeError('Master password NOT cleaned from memory !')

    def _get_password(self):
        '''
        Decrypt master user password from session.
        NOTE : After use it, remove password from memory.
        '''
        return arao_secret.helper.decrypt_from_session(self.password)

    def create_group(self, db_session, name):
        group = arao_secret.db.model.Group()
        db_session.add(group)
        db_session.flush()  # We need the Group ID to create UserGroupKey
        group_name = arao_secret.helper.to_bytes(name)
        group_key = arao_secret.helper.aes_key_gen()
        user_group_key = arao_secret.db.model.UserGroupKey(self.user, group, group_name, group_key)
        # Memory clean check
        if not arao_secret.helper.cleaned(group_name):
            raise RuntimeError('Group name NOT cleaned from memory !')
        if not arao_secret.helper.cleaned(group_key):
            raise RuntimeError('Group key NOT cleaned from memory !')
        db_session.add(user_group_key)
        db_session.commit()
        return group, user_group_key

    def get_group(self, id):
        return self.user.get_group(id)

    def get_groups(self):
        return self.user.get_groups()

    def del_group(self, db_session, name):
        # TODO
        pass

    def create_secret(self, db_session, user_group_key, name, url, login, password, comment):
        user_pass = self._get_password()
        secret = arao_secret.db.model.Secret(user_pass, user_group_key,
                                             name, url, login, password, comment)
        # Clean sensitive data from memory
        for string in (user_pass, name, url, login, password, comment):
            SecureString.clearmem(string)
        db_session.add(secret)
        db_session.commit()
        return secret

    def list_groups(self):
        '''
        Show groups.
        '''
        print('Group ID  Group Name')
        print('--------  ----------')
        user_pass = self._get_password()
        for group_key in self.user.group_keys:
            group_key_clear = group_key.get_clear(user_pass)
            print('{:8}  {}'.format(group_key_clear['group_id'], group_key_clear['group_name']))
            group_key.clear()
        SecureString.clearmem(user_pass)

    def list_secrets(self, db_session, group_id):
        '''
        Show group secrets.
        '''
        print('Secret ID  Secret Name')
        print('---------  -----------')
        group = (db_session.query(arao_secret.db.model.Group)
                 .filter(arao_secret.db.model.Group.id == group_id)
                 .one())
        group_key = (db_session.query(arao_secret.db.model.UserGroupKey)
                     .filter(arao_secret.db.model.UserGroupKey.user_id == self.user.id)
                     .filter(arao_secret.db.model.UserGroupKey.group_id == group_id)
                     .one())
        user_pass = self._get_password()
        for secret in group.secrets:
            secret_clear = secret.get_clear(user_pass, group_key, attribute='id')
            secret_clear = secret.get_clear(user_pass, group_key, attribute='name')
            print('{:9}  {}'.format(secret_clear['id'], secret_clear['name']))
            secret_clear.clear()
        SecureString.clearmem(user_pass)

    def show_secret(self, db_session, id):
        '''
        Show secret data.
        '''
        secret = (db_session.query(arao_secret.db.model.Secret)
                  .filter(arao_secret.db.model.Secret.id == id)
                  .one())
        group_key = (db_session.query(arao_secret.db.model.UserGroupKey)
                     .filter(arao_secret.db.model.UserGroupKey.user_id == self.user.id)
                     .filter(arao_secret.db.model.UserGroupKey.group_id == secret.group_id)
                     .one())
        user_pass = self._get_password()
        secret_clear = secret.get_clear(user_pass, group_key)
        print('Name: {}'.format(secret_clear['name']))
        print('URL: {}'.format(secret_clear['url']))
        print('Login: {}'.format(secret_clear['login']))
        print('Password: {}'.format(secret_clear['password']))
        print('Comments\n{}'.format(secret_clear['comment']))
        secret_clear.clear()
        SecureString.clearmem(user_pass)


