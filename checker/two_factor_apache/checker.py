"""abcd"""

import hashlib

import requests

from ctf_gameserver.checker import BaseChecker, NOTFOUND, NOTWORKING, OK, TIMEOUT

from .lib import NotWorking, Session




class TwoFactorApacheChecker(BaseChecker):
    def check_service(self):
        return OK

    def place_flag(self):
        flag = self.get_flag(self._tick).encode('utf-8')
        hashed = hashlib.sha224(flag).hexdigest()

        sess = Session(self.logger, self._ip)

        try:
            sess.register()
            self.store_yaml('data-{}'.format(self._tick), sess.login_info)
            sess.login()
            self.store_yaml('data-{}'.format(self._tick), sess.login_info)
            r = sess.session.put(sess.make_url('public/reminder', sess.login_info['user']),
                                 hashed.encode('utf-8'))
            r.raise_for_status()

            r = sess.session.put(sess.make_url(hashed, sess.login_info['user']), flag)
            r.raise_for_status()

            self.store_yaml('flagid_{}'.format(self._tick),
                            '/~{}/public/reminder'.format(sess.login_info['user']))
        except NotWorking:
            return NOTWORKING
        except requests.exceptions.HTTPError as e:
            self.logger.warning('request failed: %s', e)
            return NOTWORKING

        return OK

    def check_flag(self, tick):
        sess = Session(self.logger, self._ip, self.retrieve_yaml('data-{}'.format(tick)))
        if sess.login_info is None:
            self.logger.debug("no account data stored for tick %d", tick)
            return NOTFOUND

        flag_expect = self.get_flag(tick)
        hashed = hashlib.sha224(flag_expect.encode('utf-8')).hexdigest()

        try:
            # public data still needs a login
            temp_sess = Session(self.logger, self._ip, sess.login_info)
            try:
                self.logger.info('registering temp user to retrieve public data')
                temp_sess.register()
                temp_sess.login()
            except NotWorking:
                self.logger.warning('failed login/register of temp user')
                return NOTWORKING
            r = temp_sess.session.get(sess.make_url('public/reminder', sess.login_info['user']))
            if r.status_code == 404:
                self.logger.warning('got 404 trying to download reminder')
                return NOTFOUND
            r.raise_for_status()
            if r.text != hashed:
                self.logger.warning('wrong reminder: %s', r.text)
                return NOTFOUND

            try:
                sess.login()
            except NotWorking:
                self.logger.warning('failed to login as user %s that stored the flag',
                                    sess.login_info['user'])
                return NOTFOUND
            finally:
                self.store_yaml('data-{}'.format(tick), sess.login_info)

            r = sess.session.get(sess.make_url(hashed, sess.login_info['user']))
            if r.status_code == 404:
                self.logger.warning('got 404 trying to download flag')
                return NOTFOUND
            r.raise_for_status()
            if r.text != flag_expect:
                self.logger.warning('got unexpected flag value (%s instead of %s)', r.text,
                                    flag_expect)
                return NOTFOUND
        except requests.exceptions.HTTPError as e:
            self.logger.warning('request failed: %s', e)
            return NOTWORKING

        return OK
