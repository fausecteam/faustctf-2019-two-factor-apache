#!/usr/bin/env python3

import urllib.parse

import flup.server.fcgi_base
from flup.server.fcgi_fork import WSGIServer
from flup.server.fcgi_base import FCGI_AUTHORIZER, FCGI_RESPONDER

from .authenticate import authenticate, authorize
from .dav import dav_responder
from .register import do_register
from .show_login import show_login
from .show_register import show_register

#flup.server.fcgi_base.DEBUG = 10


def fcgi_authorizer(env, start_response):
    status, headers = b'401 ', []

    if env.get('FCGI_APACHE_ROLE') == "AUTHORIZER" and authorize(env, headers):
        status = b'200 OK'
    elif env.get('FCGI_APACHE_ROLE') == "AUTHENTICATOR" and authenticate(env, headers):
        status = b'200 OK'

    start_response(status, headers)
    return []


def fcgi_responder(env, start_response):
    if env['REQUEST_URI'] == '/cgi-bin/login':
        return show_login(env, start_response)
    elif env['REQUEST_URI'] == '/cgi-bin/sign-up':
        return show_register(env, start_response)
    elif env['REQUEST_URI'] == '/cgi-bin/do-register':
        return do_register(env, start_response)
    elif env['REQUEST_URI'] == '/cgi-bin/' or env['REQUEST_URI'].startswith('/cgi-bin/do-login?'):
        start_response(b'302 Found', [(b'Location', '/~' + urllib.parse.quote(env['REMOTE_USER']) + '/')])
        return []
    elif env['REQUEST_URI'].startswith('/~'):
        return dav_responder(env, start_response)
    else:
        start_response(b'404 Not Found', [])
        return []


def app(env, start_response):
    if env.get('FCGI_ROLE') == 'AUTHORIZER':
        return fcgi_authorizer(env, start_response)
    else:
        return fcgi_responder(env, start_response)


serv = WSGIServer(app, bindAddress=('::1', 808, 0), roles=(FCGI_AUTHORIZER, FCGI_RESPONDER))
serv.debug = False
serv.run()
