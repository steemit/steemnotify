import json
import tarantool
import os
import time
import sys

tnt_server = None


def run():
    res = tnt_server.call(
        'get_page_refs',
        '/steemit/@dcardenas/the-walking-dead-season-7'
    )
    print('res:', res)


def main():
    print('Connecting to tarantool (datastore:3301)..')
    sys.stdout.flush()

    try:
        tnt_server = tarantool.connect('localhost', 3301)
    except Exception as e:
        print('Cannot connect to tarantool server', file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.stderr.flush()
    else:
        run()


if __name__ == "__main__":
    main()
