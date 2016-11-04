require 'notifications'
require 'quota'

box.cfg {
    log_level = 5,
    listen = '0.0.0.0:3301',
    slab_alloc_arena = 8.0,
    wal_dir    = "/var/lib/tarantool",
    snap_dir   = "/var/lib/tarantool",
    vinyl_dir = "/var/lib/tarantool"
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

    quota = box.schema.create_space('quota')
    quota:create_index('primary', {type = 'tree', parts = {1, 'unsigned'}})
    quota:create_index('secondary', {
        type = 'tree',
        unique = false,
        parts = {2, 'string', 3, 'string'}
    })
end)

fiber = require 'fiber'
fiber.create(quotaGarbageCollectionFiber)

-- require('console').start()
