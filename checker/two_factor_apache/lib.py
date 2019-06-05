"""abcd"""

import string
import time
import urllib.parse
from random import SystemRandom

import numpy as np

from oath import GoogleAuthenticator

import requests

import zbar


rand = SystemRandom()


class NotWorking(Exception):
    pass


def token(length=16):
    alphabet = string.ascii_letters + string.digits
    return "".join(rand.choice(alphabet) for _ in range(length))


def qr_image(text):
    lines = text.split('\n')
    data = np.zeros((len(lines) * 2, len(lines) * 2), dtype=np.uint8)
    for line, l in enumerate(text.split('\n')[1:-2]):
        for col, c in enumerate(l[2:-2]):
            if c == '█':
                upper = 0xff
                lower = 0xff
            elif c == ' ':
                upper = 0
                lower = 0
            elif c == '▀':
                upper = 0xff
                lower = 0
            elif c == '▄':
                upper = 0
                lower = 0xff
            else:
                return None
            data[line * 2, col] = upper
            data[line * 2 + 1, col] = lower
    # resize single pixels to 8x8 blocks
    return data.repeat(8, axis=0).repeat(8, axis=1)


class Session:
    def __init__(self, logger, ip, login_info=None):
        self.ip = ip
        self.logger = logger
        self.login_info = login_info
        self.session = requests.session()

    def get_otp(self):
        auth = GoogleAuthenticator(self.login_info['oath_uri'], self.login_info['state'])
        if 'period' in auth.parsed_otpauth_uri:
            self.login_info['last'] = int(max(time.time(), self.login_info['last'] +
                                          auth.parsed_otpauth_uri['period']))
        else:
            self.login_info['last'] = int(time.time())
        otp = auth.generate(t=self.login_info['last'])
        self.login_info['state'] = auth.generator_state
        return otp

    def make_url(self, endpoint, user=None):
        if user:
            endpoint = '~' + urllib.parse.quote(user) + '/' + endpoint
        port = 80 if self.ip in ('localhost', '127.0.0.1') else 1234
        url = "http://{}:{}/{}".format(self.ip, port, endpoint)
        self.logger.info('url: %s', url)
        return url

    def register(self):
        user = token()
        password = token()
        self.logger.info('registering user %s with password %s', user, password)
        r = self.session.post(self.make_url('cgi-bin/do-register'), data={
            'user': user,
            'pass': password,
            'pass2': password,
        })
        r.raise_for_status()
        try:
            qr = qr_image(r.text.split("<pre>")[1].split("</pre>")[0])
        except IndexError:
            self.logger.warning('qr code not found in response')
            raise NotWorking()
        if qr is None:
            self.logger.warning('failed to parse text representation of qr code:\n\n%s', r.text)
            raise NotWorking()

        try:
            oath_uri = zbar.Scanner().scan(qr)[0].data.decode('utf-8')
        except (IndexError, UnicodeDecodeError):
            self.logger.warning('failed to decode qr code: %s',
                                r.text.split("<pre>")[1].split("</pre>")[0])
            raise NotWorking()

        try:
            GoogleAuthenticator(oath_uri)
        except ValueError:
            self.logger.exception("invalid otpauth:// uri")

        self.login_info = {
            'last': 0,
            'oath_uri': oath_uri,
            'state': {},
            'user': user,
            'pass': password,
        }
        self.logger.info('successfully registered new user:\n\n%s', repr(self.login_info))

    def login(self, retries=5):
        self.logger.info('retrieving csrf token for login')
        r = self.session.get(self.make_url('cgi-bin/login'))
        r.raise_for_status()
        csrf = r.text.split('<input type="hidden" name="csrf" value="')[1].split('"')[0]

        self.logger.info('before o %s', repr(self.login_info))
        token = self.get_otp()
        self.logger.info('logging in as %s (password %s) with hotp %s and csrf token %s',
                         self.login_info['user'], self.login_info['pass'], token, csrf)
        r = self.session.post(self.make_url('cgi-bin/do-login?otp=' + token), data={
            'user': self.login_info['user'],
            'pass': self.login_info['pass'],
            'csrf': csrf,
        })
        self.logger.info('login response: %s', str(r))
        r.raise_for_status()

        if r.url != self.make_url('', self.login_info['user']):
            if retries:
                self.logger.warning('retry %d after failed login: %s', 6 - retries, r.url)
                return self.login(retries - 1)
            self.logger.warning('unexpected URI after login: %s', r.url)
            raise NotWorking()

        self.logger.info('login successful (user %s)', self.login_info['user'])
