fiber = require('fiber')
-- require 'table_utils'

-- box.cfg {
--     log_level = 5,
--     listen = '0.0.0.0:3301',
--     wal_dir    = "quota-db-taran",
--     snap_dir   = "quota-db-taran",
--     vinyl_dir = "quota-db-taran"
-- }
-- 
box.once('bootstrap', function()
    
end)

QUOTA = {
    TIME = 4,
    AMOUNT = 5,
}

INFO_LOG = true

-- TODO: store in database, pull on garbageCollection
limitsByType = {
    uploadIp = {
        minute = 60,
        hour = 70,
        day = 80,
    },
    uploadData = {
        minute = 200,
        hour = 200,
        day = 300,
        week = 300,
    },
    downloadIp = {
        hour = 3600,
    },
}

seconds = {
    minute = 60,
    hour = 60 * 60,
    day =  60 * 60 * 24,
    week = 60 * 60 * 24 * 7,
}

function durations(age, cb)
    for duration, amt in pairs(seconds) do
        if age <= amt then
            cb(duration)
        end
    end
end

function aprox(duration)
    return
        duration >= seconds.week and tostring(duration / seconds.week) .. ' week' or
        duration >= seconds.day and tostring(duration / seconds.day) .. ' day' or
        duration >= seconds.hour and tostring(duration / seconds.hour) .. ' hour' or
        duration >= seconds.minute and tostring(duration / seconds.minute) .. ' minute' or
        duration .. ' second'
end

-- limits = {{duration, max}}
-- key = unique key string (ip address, username, etc..
-- description = What is being limited? 'Uploads', 'Upload size' (use capital)
-- unitLabel = A label for the amount value (requests, megabytes)
-- amount = Amount to increment quota.  Only increments if still within quota.
function limit(type, key, description, unitLabel, amount)
    if(amount == nil) then
        amount = 1
    end

    local limits = limitsByType[type]
    if not limits then
        box.error{reason = 'Unknown limit type: ' .. type}
    end

    local time = os.time()
    local tuple = {type, key, time, amount}

    box.begin()

    local quota = box.space.quota
    quota:auto_increment(tuple)

    local res = quota.index.secondary:select{type, key}
    -- print_r(res)

    local sum_by_duration = {}
    for i, row in pairs(res) do
        local age = time - row[QUOTA.TIME]
        local expired = age > seconds.week
        if not expired then
            local amt = row[QUOTA.AMOUNT]
            durations(age, function (d)
                local total = sum_by_duration[d]
                if total == nil then total = 0 end
                total = total + amt
                sum_by_duration[d] = total
            end)
        end
    end
    -- print_r(sum_by_duration)

    for _duration, _total in pairs(sum_by_duration) do
        local _max = limits[_duration]
        if _max ~= nil then
            duration = _duration
            total = _total
            max = _max

            over = total > max
            -- print(duration .. ',' .. total .. ',' .. max .. ',' .. tostring(over))
            if over then break end
        end
    end

    if over then
        box.rollback()
    else
        box.commit()
    end

    local s = seconds[duration]
    if over or INFO_LOG then
        print('Rate limiting ' .. key .. ': ' .. description ..
            (over and ' exceeded: ' or ' are within: ') ..
            total .. ' of ' .. max .. ' ' ..
            unitLabel .. ' per ' .. aprox(s)
        )
    end

    local desc = null
    if description then
        if over then
            desc = description .. ' can not exceeded ' .. max ..
            (unitLabel and ' ' .. unitLabel or '') .. ' within ' .. aprox(s)
        else
            desc = description .. ' is within ' .. max ..
            (unitLabel and ' ' .. unitLabel or '') .. ' within ' .. aprox(s)
        end
    end
    return {over = over, total = total, max = max,
        duration = duration, desc = desc}
end

-- r = limit('uploadIp', 'jimmy', 'Test calls', 'function calls', 1)
-- print_r(r)

function garbageCollection()
    print('--- quota garbageCollection ---')
    local time = os.time()

    local quota = box.space.quota
    local res = quota:select()
    -- print_r(res)

    for i, row in pairs(res) do
        local type = row[2]
        local limits = limitsByType[type]
        local max =
            limits.week ~= nil and seconds.week or
            limits.day ~= nil and seconds.day or
            limits.hour ~= nil and seconds.hour or
            seconds.minute

        local age = time - row[QUOTA.TIME]
        local expired = age > max
        -- print(type .. ',' .. age .. ',' .. max .. ',' .. tostring(expired))
        if expired then
            quota:delete(row[1])
        end
    end
end

function garbageCollectionFiber()
    while 0 == 0 do
        garbageCollection()
        fiber.sleep(seconds.minute) -- hour
    end
end
gcObject = fiber.create(garbageCollectionFiber)
