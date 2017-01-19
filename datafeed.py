print('starting datafeed.py..')

import json
import tarantool
import os
import time
import sys
import re
from contextlib import suppress
from steem import Steem
from steem.blockchain import Blockchain
from steem.account import Account

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

tnt_server = None
steem_space = None
followers_space = None
chain = None

def _get_followers(account, direction='follower', last_user=''):
    if direction == 'follower':
        followers = account.get_followers()
    elif direction == 'following':
        followers = account.get_following()
    return followers

def getFollowers(account):
    # print('getFollowers', account.name)
    global followers_space
    res = followers_space.select(account.name)
    if len(res) == 0:
        followers = _get_followers(account)
        followers_space.insert((account.name, followers))
    else:
        followers = res[0][1]
    return followers

def addFollower(account_name, follower):
    # print('addFollower', account_name, follower)
    global tnt_server
    global followers_space
    res = tnt_server.call('add_follower', account_name, follower)
    if not res[0][0]:
        with suppress(Exception):
            followers = _get_followers(Account(account_name))
            followers.append(follower)
            followers_space.insert((account_name, followers))
            tnt_server.call('add_follower', account_name, follower)

def processMentions(author_account, text, op):
    mentions = re.findall('\@[\w\d.-]+', text)
    if (len(mentions) == 0):
        return
    # print('\nop: ', op)
    if op['parent_author']:
        what = 'comment'
        url = 'https://steemit.com/@%s/%s#@%s/%s' % (op['parent_author'], op['parent_permlink'], op['author'], op['permlink'])
    else:
        what = 'post'
        url = 'https://steemit.com/@%s/%s' % (op['author'], op['permlink'])
    for mention in set(mentions):
        if (mention != op['author']):
            # print('--- mention: ', what, url, mention, mention[1:])
            title = 'Steemit'
            body = '@%s mentioned you in %s' % (op['author'], what)
            profile = author_account.profile
            pic = profile['profile_image'] if profile and 'profile_image' in profile else ''
            tnt_server.call('notification_add', mention[1:], NTYPES['mention'], title, body, url, pic)

def processOp(op_data):
    op_type = op_data[0]
    op = op_data[1]
    if op_type == 'custom_json' and op['id'] == 'follow':
        op_json = json.loads(op['json'])
        if isinstance(op_json, list) and op_json[0] == 'follow':
            data = op_json[1]
            addFollower(data['following'], data['follower'])
            tnt_server.call('notification_add', data['following'], NTYPES['follow'])
    if op_type == 'comment':
        comment_body = op['body']
        if comment_body and not comment_body.startswith('@@ '):
            with suppress(Exception):
                author_account = Account(op['author'])
                if op['parent_author']:
                    # print('comment', op['author'], op['parent_author'])
                    title = 'Steemit'
                    body = '@%s replied to your post or comment' % (op['author'])
                    url = 'https://steemit.com/@%s/recent-replies' % (op['parent_author'])
                    profile = author_account.profile
                    pic = profile['profile_image'] if profile and 'profile_image' in profile else ''
                    tnt_server.call('notification_add', op['parent_author'], NTYPES['comment_reply'], title, body, url, pic)
                else:
                    # print('post', op)
                    followers = getFollowers(author_account)
                    for follower in followers:
                        tnt_server.call('notification_add', follower, NTYPES['feed'])
                processMentions(author_account, comment_body, op)
    if op_type.startswith('transfer'):
        if op['from'] != op['to']:
            # print(op_type, op['from'], op['to'])
            title = 'Steemit'
            body = 'you transfered %s to @%s' % (op['amount'], op['to'])
            url = 'https://steemit.com/@%s/transfers' % (op['from'])
            tnt_server.call('notification_add', op['from'], NTYPES['send'], title, body, url, '')
            body = 'you received %s from @%s' % (op['amount'], op['from'])
            url = 'https://steemit.com/@%s/transfers' % (op['to'])
            tnt_server.call('notification_add', op['to'], NTYPES['receive'], title, body, url, '')
    if op_type == 'account_update' and ('active' in op or 'owner' in op or 'posting' in op):
        #print(json.dumps(op, indent=4))
        title = 'Steemit'
        body = 'account @%s has been updated or password changed' % (op['account'])
        url = 'https://steemit.com/@%s/permissions' % (op['account'])
        tnt_server.call('notification_add', op['account'], NTYPES['account_update'], title, body, url, '')
    # if op_type == 'vote':
        # print('----', op['voter'], op['permlink'])

def run():
    global steem
    global steem_space
    last_block = 8446170
    last_block_id_res = steem_space.select('last_block_id')
    if len(last_block_id_res) != 0:
        last_block = last_block_id_res[0][1]
        print('last_block', last_block)
    else:
        steem_space.insert(('last_block_id', last_block))

    for block in chain.blocks(start=last_block):
        # print(json.dumps(block, indent=4))
        if last_block % 10 == 0:
            print('processing block', last_block)
            sys.stdout.flush()
        for t in block['transactions']:
            for op in t['operations']:
                # if op[0] not in ['comment', 'vote', 'custom_json', 'pow2', 'account_create', 'limit_order_create', 'limit_order_cancel', 'feed_publish', 'comment_options', 'account_witness_vote', 'account_update'] and not op[0].startswith('transfer'):
                #     print('---------', op[0])
                #     print(json.dumps(op[1], indent=4))
                processOp(op)
        last_block += 1
        steem_space.update('last_block_id', [('=', 1, last_block)])


ws_connection = os.environ['WS_CONNECTION']
print('Connecting to ', ws_connection)
sys.stdout.flush()
steem = Steem(ws_connection)
chain = Blockchain(steem_instance=steem)

print('Connecting to tarantool (datastore:3301)..')
sys.stdout.flush()

while True:
    try:
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
