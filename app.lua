fiber = require 'fiber'
require 'notifications'
require 'locks'
require 'stats'

io.output():setvbuf("no")

box.cfg {
    log_level = 5,
    listen = '0.0.0.0:3301',
    slab_alloc_arena = 1.0,
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

    webpush_subscribers = box.schema.create_space('webpush_subscribers')
    webpush_subscribers:create_index('primary', {type = 'tree', parts = {1, 'STR'}})

    notifications_delivery_queue = box.schema.create_space('notifications_delivery_queue')
    notifications_delivery_queue:create_index('primary', {type = 'tree', parts = {1, 'unsigned'}})

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
    refs = box.schema.create_space('refs')
    refs:create_index('primary', {type = 'tree', parts = {1, 'unsigned'}})
    refs:create_index('by_ref', {type = 'tree', unique = false, parts = {2, 'unsigned'}})
    refs:create_index('by_page', {type = 'tree', unique = false, parts = {3, 'unsigned'}})

    quota = box.schema.create_space('quota')
    quota:create_index('primary', {type = 'tree', parts = {1, 'unsigned'}})
    quota:create_index('secondary', {
        type = 'tree',
        unique = false,
        parts = {2, 'string', 3, 'string'}
    })
end)

-- require('console').start()
