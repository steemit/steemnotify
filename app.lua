require 'notifications'
require 'quota'
require 'locks'
require 'stats'

io.output():setvbuf("no")

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

    locks = box.schema.create_space('locks')
    locks:create_index('primary', {type = 'tree', parts = {1, 'STR'}})

    -- stats spaces
    pages = box.schema.create_space('pages')
    pages:create_index('primary', {type = 'tree', parts = {1, 'unsigned'}})
    pages:create_index('secondary', {
        type = 'tree',
        unique = true,
        parts = {2, 'string'}
    })
    unique_page_views = box.schema.create_space('unique_page_views')
    unique_page_views:create_index('primary', {type = 'hash', parts = {1, 'unsigned', 2, 'string'}})

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
