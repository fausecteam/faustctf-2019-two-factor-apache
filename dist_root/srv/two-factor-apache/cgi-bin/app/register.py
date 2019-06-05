import pwd
import socket
import string
import urllib.parse
from base64 import b32encode
from fcntl import LOCK_EX, LOCK_UN, lockf
from subprocess import PIPE, run

from .utils import parse_post, show_template, token


def new_oath(user):
    assert not any(c.isspace() for c in user)
    hostname = urllib.parse.quote_plus(socket.gethostname())

    key = token(alphabet=string.digits + 'abcdef', bits=256)

    key_b32 = urllib.parse.quote_plus(b32encode(bytes.fromhex(key)).decode('utf-8'))
    user_encoded = urllib.parse.quote_plus(user)
    url_fmt = 'otpauth://totp/{user_encoded}@{hostname}?digits=8&period=30&secret={key_b32}'
    url = url_fmt.format(**locals()).encode('utf-8')
    qr = run(['qrencode', '-o', '-', '-t', 'UTF8'], input=url, check=True, stdout=PIPE)

    with open('/etc/liboath/users.oath', 'a') as f:
        lockf(f.fileno(), LOCK_EX)
        try:
            f.write('HOTP/T30/8 {user} - {key}\n'.format(**locals()))
            f.flush()
        finally:
            lockf(f, LOCK_UN)

    return qr.stdout


def register(name, password):
    try:
        pwd.getpwnam(name)
        return False
    except KeyError:
        pass
    if '\0' in password or ':' in password or ':' in name or '\0' in name or name in ('.', '..'):
        return False

    cmd = "{name}:{password}::web_users:user from web:/home/{name}:/sbin/nologin"
    run(['newusers'], input=cmd.format(**locals()).encode('utf-8'))

    return True


def do_register(env, start_response):
    if env['REQUEST_METHOD'] != 'POST':
        start_response(b'302 Found', [(b'Location', '/cgi-bin/sign-up')])
        return []

    post = parse_post(env)
    name = post.get(b'user', [b''])[0].decode('utf-8')
    password = post.get(b'pass', [b''])[0].decode('utf-8')
    password2 = post.get(b'pass2', [b''])[0].decode('utf-8')

    if not name or password != password2:
        start_response(b'302 Found', [(b'Location', '/cgi-bin/sign-up')])
        return []

    if register(name, password):
        qr_data = new_oath(name).decode('utf8')
        return show_template('registered', {'qr': qr_data, 'user': name}, [], start_response)
    else:
        start_response(b'409 Conflict', [])
        return []
