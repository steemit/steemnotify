require 'notifications'

box.cfg {
    log_level = 5;
    listen = '0.0.0.0:3313';
}

box.once('bootstrap', function()
    print('initializing..')
    box.schema.user.grant('guest', 'read,write,execute', 'universe')

    steem = box.schema.create_space('steem')
    steem:create_index('primary', {type = 'tree', parts = {1, 'STR'}})

    followers = box.schema.create_space('followers')
    followers:create_index('primary', {type = 'tree', parts = {1, 'STR'}})

    notifications = box.schema.create_space('notifications')
    notifications:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end)

require('console').start()
