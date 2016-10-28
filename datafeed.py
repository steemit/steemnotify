from steemapi.steemnoderpc import SteemNodeRPC
import json
import tarantool
import os


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

tnt_server = tarantool.connect('datastore', 3301)
steem_space = tnt_server.space('steem')
followers_space = tnt_server.space('followers')

ws_connection = os.environ['WS_CONNECTION']

print('Connecting to ', ws_connection)

steem = SteemNodeRPC(ws_connection, apis = ['database_api', 'login_api', 'follow_api'])

def _get_followers(account_name, direction='follower', last_user=''):
    if direction == 'follower':
        followers = steem.get_followers(account_name, last_user, 'blog', 100, api='follow')
    elif direction == 'following':
        followers = steem.get_following(account_name, last_user, 'blog', 100, api='follow')
    if len(followers) == 100:
        followers += _get_followers(account_name, last_user=followers[-1][direction])[1:]
    return followers

def getFollowers(account_name):
    print('getFollowers', account_name)
    global followers_space
    res = followers_space.select(account_name)
    if len(res) == 0:
        followers = [x['follower'] for x in _get_followers(account_name)]
        followers_space.insert((account_name, followers))
    else:
        followers = res[0][1]
    return followers

def addFollower(account_name, follower):
    print('addFollower', account_name, follower)
    global tnt_server
    global followers_space
    res = tnt_server.call('add_follower', account_name, follower)
    print('addFollower ->', account_name, follower, res[0][0])
    if not res[0][0]:
        followers = [x['follower'] for x in _get_followers(account_name)]
        followers.append(follower)
        followers_space.insert((account_name, followers))
        tnt_server.call('add_follower', account_name, follower)

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
        if op['parent_author']:
            print('comment', op['author'], op['parent_author'])
            tnt_server.call('notification_add', op['parent_author'], NTYPES['comment_reply'])
        else:
            print('post', op['author'])
            followers = getFollowers(op['author'])
            for follower in followers:
                # print('----',follower, NTYPES['feed'])
                tnt_server.call('notification_add', follower, NTYPES['feed'])


last_block = 6231870
last_block_id_res = steem_space.select('last_block_id')
if len(last_block_id_res) != 0:
    last_block = last_block_id_res[0][1]
    print('last_block', last_block)
else:
    steem_space.insert(('last_block_id', last_block))

for block in steem.block_stream(start=last_block, mode='irreversible'):
    # print('-----')
    # print(json.dumps(block, indent=4))
    for t in block['transactions']:
        for op in t['operations']:
            # print(op)
            processOp(op)
    last_block += 1
    steem_space.update('last_block_id', [('=', 1, last_block)])
