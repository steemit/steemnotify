#!/usr/bin/env python
import json
import os
import re
import sys
import time
from contextlib import suppress

import tarantool
from steem.account import Account
from steem.blockchain import Blockchain
from steem.post import Post
from steembase.exceptions import PostDoesNotExist

MIN_NOTIFY_REPUTATION = 40

NTYPES = {
    'total': 0,
    'feed': 1,
    'reward': 2,
    'send': 3,
    'mention': 4,
    'follow': 5,
    'vote': 6,
    'comment_reply': 7,
    'post_reply': 8,
    'account_update': 9,
    'message': 10,
    'receive': 11
}

# gloabal variables
tnt_server = None
steem_space = None
followers_space = None
chain = None
img_proxy_prefix = os.getenv('IMG_PROXY_PREFIX')
processed_posts = {}


def getPostKey(post):
    try:
        if not post.meta or \
                not isinstance(post.meta, dict) or \
                'tags' not in post.meta or \
                len(post.meta['tags']) == 0:
            return None

        return '/%s/@%s/%s' % (
            post.meta['tags'][0],
            post.author,
            post.permlink
        )
    except PostDoesNotExist:
        return None


def getFollowersWithDirection(account, direction='follower', last_user=''):
    if direction == 'follower':
        followers = account.get_followers()
    elif direction == 'following':
        followers = account.get_following()
    return followers


def getFollowers(account):
    # print('getFollowers', account.name)
    res = followers_space.select(account.name)
    if len(res) == 0:
        followers = getFollowersWithDirection(account)
        followers_space.insert((account.name, followers))
    else:
        followers = res[0][1]
    return followers


def addFollower(account_name, follower):
    # print('addFollower', account_name, follower)
    res = tnt_server.call('add_follower', account_name, follower)
    if not res[0][0]:
        with suppress(Exception):
            followers = getFollowersWithDirection(Account(account_name))
            followers.append(follower)
            followers_space.insert((account_name, followers))
            tnt_server.call('add_follower', account_name, follower)


def processMentions(author_account, text, op):
    mentions = re.findall('\@[\w\d.-]+', text)
    if len(mentions) == 0:
        return
    # print('\nop: ', op)
    if op['parent_author']:
        what = 'comment'
        url = 'https://steemit.com/@%s/%s#@%s/%s' % (
            op['parent_author'],
            op['parent_permlink'],
            op['author'],
            op['permlink']
        )
    else:
        what = 'post'
        url = 'https://steemit.com/@%s/%s' % (op['author'], op['permlink'])

    for mention in set(mentions):
        if mention == op['author']:
            # don't notify on self-mentions
            continue
        # print('--- mention: ', what, url, mention, mention[1:])
        title = 'Steemit'
        body = '@%s mentioned you in a %s' % (op['author'], what)
        profile = author_account.profile
        pic = img_proxy_prefix + profile['profile_image'] \
            if profile and 'profile_image' in profile else ''
        tnt_server.call(
            'notification_add',
            mention[1:],
            NTYPES['mention'],
            title,
            body,
            url,
            pic
        )


def processFollow(op):
    op_json = json.loads(op['json'])
    if not isinstance(op_json, list) or op_json[0] != 'follow':
        return
    data = op_json[1]
    addFollower(data['following'], data['follower'])
    tnt_server.call(
        'notification_add',
        data['following'],
        NTYPES['follow']
    )


def processComment(op):
    comment_body = op['body']
    if not comment_body or comment_body.startswith('@@ '):
        return
    post = Post(op)
    pkey = getPostKey(post)
    # print('post: ', pkey)
    if not pkey or pkey in processed_posts:
        return
    processed_posts[pkey] = True
    author_account = Account(op['author'])
    if author_account.rep < MIN_NOTIFY_REPUTATION:
        # no notifications for low-rep accounts
        return
    processMentions(author_account, comment_body, op)
    if op['parent_author']:
        if op['parent_author'] != op['author']:
            # no need to notify self of own comments
            title = 'Steemit'
            body = '@%s replied to your post or comment' % (op['author'])
            url = 'https://steemit.com/@%s/recent-replies' % (
                op['parent_author']
            )
            profile = author_account.profile
            pic = img_proxy_prefix + profile['profile_image'] \
                if profile and 'profile_image' in profile else ''
            tnt_server.call(
                'notification_add',
                op['parent_author'],
                NTYPES['comment_reply'],
                title,
                body,
                url,
                pic
            )
    else:
        followers = getFollowers(author_account)
        for follower in followers:
            tnt_server.call('notification_add', follower, NTYPES['feed'])


def processTransfer(op):
    if op['from'] == op['to']:
        return
    # print(op_type, op['from'], op['to'])
    title = 'Steemit'
    body = 'you transfered %s to @%s' % (op['amount'], op['to'])
    url = 'https://steemit.com/@%s/transfers' % (op['from'])
    tnt_server.call(
        'notification_add',
        op['from'],
        NTYPES['send'],
        title,
        body,
        url,
        ''
    )
    body = 'you received %s from @%s' % (op['amount'], op['from'])
    url = 'https://steemit.com/@%s/transfers' % (op['to'])
    tnt_server.call(
        'notification_add',
        op['to'],
        NTYPES['receive'],
        title,
        body,
        url,
        ''
    )


def processAccountUpdate(op):
    # print(json.dumps(op, indent=4))
    if not ('active' in op or 'owner' in op or 'posting' in op):
        return

    title = 'Steemit'
    body = 'account @%s has been updated or had its password changed' % (
        op['account']
    )
    url = 'https://steemit.com/@%s/permissions' % (op['account'])
    tnt_server.call(
        'notification_add',
        op['account'],
        NTYPES['account_update'],
        title,
        body,
        url,
        ''
    )


def processOp(op):
    op_type = op['type']

    if op_type == 'custom_json' and op['id'] == 'follow':
        processFollow(op)

    if op_type == 'comment':
        processComment(op)

    if op_type.startswith('transfer'):
        processTransfer(op)

    if op_type == 'account_update':
        processAccountUpdate(op)


def run():
    last_block = chain.info()['head_block_number']
    last_block_id_res = steem_space.select('last_block_id')
    if len(last_block_id_res) != 0:
        last_block = last_block_id_res[0][1]
        print('last_block', last_block)
    else:
        steem_space.insert(('last_block_id', last_block))

    for op in chain.replay(start_block=last_block):
        if last_block % 10 == 0:
            print('processing block', last_block)
            sys.stdout.flush()

        processOp(op)

        if last_block != op['block_num']:
            last_block = op['block_num']
            steem_space.update('last_block_id', [('=', 1, last_block)])


def main():
    global tnt_server
    global steem_space
    global followers_space
    global chain

    print('starting datafeed.py..')
    sys.stdout.flush()

    chain = Blockchain(mode='head')

    while True:
        try:
            print('Connecting to tarantool (datastore:3301)..')
            sys.stdout.flush()
            tnt_server = tarantool.connect('datastore', 3301)
            steem_space = tnt_server.space('steem')
            followers_space = tnt_server.space('followers')
        except Exception as e:
            print('Cannot connect to tarantool server', file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.stderr.flush()
            time.sleep(10)
            continue
        else:
            while True:
                run()
                print('[run] exited, continue..')


if __name__ == "__main__":
    main()
