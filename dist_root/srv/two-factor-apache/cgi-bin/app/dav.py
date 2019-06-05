""" Well, this isn't really WebDAV - didn't feel like all that XML... """

import errno
import html
from os import chmod, listdir, mkdir, rename, rmdir, setegid, seteuid, stat, unlink
from os.path import basename, dirname, isdir, join
from pwd import getpwnam
from tempfile import NamedTemporaryFile

import magic

from .utils import show_template


def dav_GET(path, env, start_response):
    if not dav_HEAD(path, env, start_response):
        return

    try:
        with open(path, 'rb') as f:
            while True:
                d = f.read(1024*1024)
                if not d:
                    break
                yield d
    except IsADirectoryError:
        yield from show_template('dir_pre', {'path': html.escape(path)}, None, None)

        fmt = "<a href='{0}' class='list-group-item list-group-item-action'>{0}</a>"

        yield "<a href='.' class='list-group-item list-group-item-action active'>.</a>"
        yield fmt.format('..')
        for entry in listdir(path):
            yield fmt.format(html.escape(entry))

        yield from show_template('dir_post', {}, None, None)


def dav_HEAD(path, env, start_response):
    try:
        meta = stat(path)
    except FileNotFoundError:
        start_response(b'404 Not Found', [])
        return False
    except PermissionError:
        start_response(b'403 Forbidden', [])
        return False
    except OSError:
        start_response(b'500 Internal Server Error', [])
        return False

    mime = magic.mime_magic.file(path)
    if mime is None:
        start_response(b'500 Internal Server Error', [])
        return False

    if mime == 'inode/directory; charset=binary':
        canon_url = env['REQUEST_URI'] + '/'
        headers = [(b'Content-Type', b'text/html; charset=utf-8')]
    else:
        headers = [
            (b'Content-Type', mime),
            (b'Content-Length', str(meta.st_size))
        ]
        canon_url = env['REQUEST_URI']
    canon_url = canon_url.replace('//', '/').replace('//', '/')
    if env['REQUEST_URI'] != canon_url:
        start_response(b'302 Found', [(b'Location', canon_url)])
        return False

    start_response(b'200 OK', headers)
    return True


def dav_PUT(home, path, env, start_response):
    try:
        path_dir = '/'
        public = False
        for d in path.split('/')[:-1]:
            path_dir += d + '/'
            if d == 'public':
                public = True
            if not isdir(path_dir):
                mkdir(path_dir, mode=0o750 if public else 0o710)

        with NamedTemporaryFile(prefix=basename(path), dir=path_dir, delete=False) as f:
            try:
                chmod(f.name, 0o640 if public else 0o600)

                written = 0
                while True:
                    d = env['wsgi.input'].read(1024 * 1024)
                    if not d:
                        break
                    f.write(d)
                    written += len(d)
                    if written > 1024*1024:
                        raise OSError('quota exceeded')
                f.flush()
                rename(f.name, path)
            except Exception as e:
                unlink(f.name)
                raise e
    except FileNotFoundError:
        start_response(b'404 Not Found', [])
        return []
    except PermissionError:
        start_response(b'403 Forbidden', [])
        return []
    except OSError:
        start_response(b'500 Internal Server Error', [])
        return []

    start_response(b'201 Created', [])
    return []


def dav_DELETE(path, env, start_response):
    try:
        try:
            unlink(path)
        except IsADirectoryError:
            rmdir(path)
    except FileNotFoundError:
        start_response(b'404 Not Found', [])
        return []
    except PermissionError:
        start_response(b'403 Forbidden', [])
        return []
    except OSError:
        start_response(b'500 Internal Server Error', [])
        return []

    start_response(b'204 No Content', [])
    return []


def dav_responder(env, start_response):
    user, _, path = env['REQUEST_URI'][2:].partition('/')
    try:
        pw = getpwnam(user)
    except KeyError:
        start_response(b'404 Not Found', [])
        return []

    path = join(pw.pw_dir, path)

    setegid(pw.pw_gid)
    seteuid(pw.pw_uid)

    try:
        if env['REQUEST_METHOD'] == 'GET':
            return dav_GET(path, env, start_response)
        elif env['REQUEST_METHOD'] == 'HEAD':
            dav_HEAD(path, env, start_response)
            return []
        elif env['REQUEST_METHOD'] == 'PUT':
            return dav_PUT(pw.pw_dir, path, env, start_response)
        elif env['REQUEST_METHOD'] == 'DELETE':
            return dav_DELETE(path, env, start_response)
        else:
            start_response(b'405 Method Not Allowed', [])
            return []
    finally:
        seteuid(0)
        setegid(0)
