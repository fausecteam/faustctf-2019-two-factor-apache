import fcntl
import os
import sys
import urllib.parse

from pamela import PAMError, PAM_AUTHENTICATE, PAM_REINITIALIZE_CRED, PAM_SETCRED, \
        new_simple_password_conv, pam_end, pam_start


def pam_auth(user, *secrets):
    pid = os.fork()
    # PAM stack does weird stuff with process credentials and umask, so do it in a subprocess
    if pid == 0:
        conv = new_simple_password_conv(secrets, 'utf-8')

        try:
            handle = pam_start('2fapache', user, conv_func=conv, encoding='utf-8')

            fd = os.open('/tmp/lock', os.O_WRONLY | os.O_CREAT)
            # pam_oath can't handle concurrent logins correctly
            # (OATH_FILE_UNLINK_ERROR: System error when removing file)
            fcntl.lockf(fd, fcntl.LOCK_EX)
            try:
                retval = PAM_AUTHENTICATE(handle, 0)
                # Re-initialize credentials (for Kerberos users, etc)
                # Don't check return code of pam_setcred(), it shouldn't matter
                # if this fails
                if retval == 0 and PAM_REINITIALIZE_CRED:
                    PAM_SETCRED(handle, PAM_REINITIALIZE_CRED)
            finally:
                fcntl.lockf(fd, fcntl.LOCK_UN)
                os.close(fd)

            pam_end(handle, retval)
            os._exit(retval)
        except PAMError as e:
            print(e, file=sys.stderr)
            os._exit(1)
    else:
        pid, res = os.waitpid(pid, 0)
        return os.WIFEXITED(res) and os.WEXITSTATUS(res) == 0


def authorize(env, headers):
    return 'REMOTE_USER' in env


def parse_get(env):
    return urllib.parse.parse_qs(env.get('QUERY_STRING', ''))


def authenticate(env, headers):
    if not env['REQUEST_URI'].startswith('/cgi-bin/do-login?'):
        # Apache redirects anyone without a valid auth cookie to the login page
        # so no point in re-authenticating every request
        print('already logged in - skipping authentication', file=sys.stderr)
        return True

    # Apache doesn't pass along post data during the authentication phase, so we have to get otp
    # from a GET param. That's fine because HOTPs become invalid after being used.
    otp = parse_get(env).get('otp', [None])[0]
    print('authenticating {} {} {}'.format(repr(env['REMOTE_USER']), repr(env['REMOTE_PASSWD']),
                                           repr(otp)),
          file=sys.stderr)
    return otp and pam_auth(env['REMOTE_USER'], otp, env['REMOTE_PASSWD'])
