from steemtools.blockchain import Blockchain
from steemtools.node import Node
from steemtools.base import Account
from dateutil import parser
from steemtools.helpers import read_asset, parse_payout, time_diff
import json
import tarantool

node = Node()
node._nodes = {
            "local": ["ws://127.0.0.1:8090"],
            "public": ["wss://steemit.com/wspa"],
        }
print(node._nodes)

tnt_server = tarantool.connect('localhost', 3313)
steem_space = tnt_server.space('steem')
followers_space = tnt_server.space('followers')

def getFollowers(account_name):
    global followers_space
    res = followers_space.select(account_name)
    if len(res) == 0:
        account = Account(account_name)
        followers = account.get_followers()
        followers_space.insert((account_name, followers))
    else:
        followers = res[0][1]
    return followers

def addFollower(account_name, follower):
    global tnt_server
    global followers_space
    res = tnt_server.call('add_follower', account_name, follower)
    print('addFollower ->', account_name, follower, res[0][0])
    if not res[0][0]:
        account = Account(account_name)
        followers = account.get_followers()
        followers.append(follower)
        followers_space.insert((account_name, followers))
        tnt_server.call('add_follower', account_name, follower)


NTYPES = {
  'total': 0,
  'feed': 1,
  'reward': 2,
  'transfer': 3,
  'mention': 4,
  'follow': 5,
  'vote': 6,
  'comment_reply': 7,
  'post_reply': 8,
  'key_update': 9,
  'message': 10
}

# tnt_server.call('notification_add', 'account5', NTYPES['follow'])
# tnt_server.call('notification_add', 'account5', NTYPES['follow'])
# tnt_server.call('notification_add', 'account5', NTYPES['follow'])
# res = tnt_server.call('notification_add', 'account7', NTYPES['transfer'])
# print('result:', res)
# tnt_server.call('notification_add', 'account6', NTYPES['follow'])
# tnt_server.call('notification_add', 'account6', NTYPES['follow'])
#
# res = tnt_server.call('notification_read', 'account5', NTYPES['transfer'])
# # res = tnt_server.call('notification_read', 'account6', NTYPES['follow'])
# print('result:', res)

# print(getAccountFollowers('furion'))


# Event: vote
# Time: 2016-09-28T19:11:54
# OP: {'permlink': 'crazychallenge-the-first-season-the-eleventh-game-contest-with-money-prize', 'weight': 10000, 'voter': 'nadin3', 'author': 'anasya'}
#
# Event: custom_json
# Time: 2016-09-28T19:11:54
# OP: {'required_auths': [], 'id': 'follow', 'required_posting_auths': ['merej99'], 'json': '["follow",{"follower":"merej99","following":"l0k1","what":["blog"]}]'}
#
# Event: comment
# Time: 2016-09-28T19:12:09
# OP: {'title': 'Turismo en Venezuela', 'body': '...', 'parent_permlink': 'turismo', 'author': 'osmi', 'permlink': 'turismo-en-venezuela', 'json_metadata': '{"tags":["turismo","venezuela","pais","paisajes",""],"image":["http://fotos2013.cloud.noticias24.com/saltoangel_88.jpg"]}', 'parent_author': ''}
#
# Event: comment
# Time: 2016-09-28T19:12:33
# OP: {'title': '', 'body': 'Hilarious thanks to you. Aside from devaluing paper notes..they get smaller in sizes too.', 'parent_permlink': 'the-value-of-money-today-is-not-the-same-in-the-future', 'author': 'immarojas', 'permlink': 're-nasimbabu-the-value-of-money-today-is-not-the-same-in-the-future-20160928t193004926z', 'json_metadata': '{"tags":["money"]}', 'parent_author': 'nasimbabu'}
#
# Event: transfer
# Time: 2016-09-28T19:12:12
# OP: {'from': 'rolik', 'memo': '', 'amount': '8.000 STEEM', 'to': 'testselo'}


start_block = 6173644
last_block_id_res = steem_space.select('last_block_id')
if len(last_block_id_res) != 0:
    print('last_block_id', last_block_id_res[0])
    start_block = last_block_id_res[0][1]
    print('start_block', start_block)
else:
    steem_space.insert(('last_block_id', start_block))

for event in Blockchain(node.public()).replay(start_block): #, filter_by=["vote", "comment"]
    op_type = event['op_type']
    # print(event)
    # continue
    op = event['op']
    if op_type == 'custom_json' and op['id'] == 'follow':
        op_json = json.loads(op['json'])
        if isinstance(op_json, list) and op_json[0] == 'follow':
            # print("Event: %s" % event['op_type'])
            # print("Time: %s" % event['timestamp'])
            # print("OP: %s\n" % op)
            data = op_json[1]
            addFollower(data['following'], data['follower'])
            tnt_server.call('notification_add', data['following'], NTYPES['follow'])
    if op_type == 'comment':
        if op['parent_author']:
            print(event['timestamp'], 'comment', op['author'], op['parent_author'])
            tnt_server.call('notification_add', op['parent_author'], NTYPES['comment_reply'])
        else:
            print(event['timestamp'], 'post', op['author'])
            followers = getFollowers(op['author'])
            for follower in followers:
                # print('----',follower, NTYPES['feed'])
                tnt_server.call('notification_add', follower, NTYPES['feed'])
    steem_space.update('last_block_id', [('=', 1, event['block_id'])])
