import math
import os.path
import string
import urllib.parse
from random import SystemRandom
random = SystemRandom()


def show_template(name, fmt, headers, start_response):
    if start_response:
        headers.append((b'Content-Type', b'text/html; charset=utf-8'))
        start_response(b'200 OK', headers)
    name = os.path.join(os.path.dirname(__file__), name + '.in')
    out = []
    with open(name, 'r') as f:
        for l in f:
            out.append(l.format(**fmt).encode('utf-8'))
    return out


def token(*, length=None, alphabet=string.ascii_letters + string.digits, bits=None):
    if length is None:
        if bits is None:
            length = 30
        else:
            char_bits = math.log2(len(alphabet))
            length = 1
            length = math.ceil(bits / char_bits)
            # just in case floats are being weird:
            while (len(alphabet) ** length).bit_length() < bits:
                length += 1
    else:
        assert bits is None

    return "".join(random.choice(alphabet) for _ in range(length))


def parse_post(env):
    try:
        request_body_size = int(env.get('CONTENT_LENGTH', 0))
    except ValueError:
        request_body_size = 0

    # print(repr(request_body_size), file=sys.stderr)
    request_body = env['wsgi.input'].read(request_body_size)
    # print(repr(request_body), file=sys.stderr)
    d = urllib.parse.parse_qs(request_body)
    # print(repr(d), file=sys.stderr)
    return d
