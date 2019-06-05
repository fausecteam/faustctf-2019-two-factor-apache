import html
from urllib.parse import parse_qs, urlencode

from .utils import show_template, token


def show_register(env, start_response):
    session = parse_qs(env.get('HTTP_SESSION', ''))
    session['csrf'] = token()
    headers = [(b'Replace-Session', urlencode(session, doseq=True))]

    form_data = {
        'user': [''],
    }
    form_data.update(parse_qs(env.get('wsgi.stdin'), ''))
    form_data['csrf_token'] = session['csrf']
    form_data = {k: html.escape(v[0]) for k, v in form_data.items()}

    return show_template('register', form_data, headers, start_response)
