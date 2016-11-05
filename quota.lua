-- require 'table_utils'

-- Usage
-- r = limit('uploadIp', 'jimmy', 'Test calls', 'function calls', 1)
-- print_r(r) --> {over = over, total = total, max = max, duration = duration, desc = desc}

local QUOTA = {
    TIME = 4,
    AMOUNT = 5,
}

local INFO_LOG = true

-- TODO: store in database, pull on garbageCollection
local limitsByType = {
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

local seconds = {
    minute = 60,
    hour = 60 * 60,
    day =  60 * 60 * 24,
    week = 60 * 60 * 24 * 7,
}

local function durations(age, cb)
    for duration, amt in pairs(seconds) do
        if age <= amt then
            cb(duration)
        end
    end
end

local function aprox(duration)
    return
        duration >= seconds.week and tostring(duration / seconds.week) .. ' week' or
        duration >= seconds.day and tostring(duration / seconds.day) .. ' day' or
        duration >= seconds.hour and tostring(duration / seconds.hour) .. ' hour' or
        duration >= seconds.minute and tostring(duration / seconds.minute) .. ' minute' or
        duration .. ' second'
end

-- limitType = uploadIp|uploadData
-- key = string: ip address, username, etc..
-- description = What is being limited? 'Uploads', 'Upload size' (use capital)
-- unitLabel = A label for the amount value (requests, megabytes)
-- amount = Amount to increment quota.  Only increments if still within quota.
function limit(limitType, key, description, unitLabel, amount)
    local limits = limitsByType[limitType]
    if not limits then
        box.error{reason = 'Unknown limit type: ' .. tostring(limitType)}
    end

    if key == nil or key == '' then
        box.error{reason = 'key is required'}
    end

    if(amount == nil) then
        amount = 1
    end
    if(type(amount) ~= 'number') then
        box.error{reason = 'Amount is a required number: ' .. tostring(amount)}
    end

    local time = os.time()
    local tuple = {limitType, key, time, amount}

    box.begin()

    local quota = box.space.quota
    quota:auto_increment(tuple)

    local res = quota.index.secondary:select{limitType, key}
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

local function garbageCollection()
    -- print('Quota garbage collection running...')
    local time = os.time()

    local quota = box.space.quota
    local res = quota:select()
    -- print_r(res)

    for i, row in pairs(res) do
        local limitType = row[2]
        local limits = limitsByType[limitType]
        local max =
            limits.week ~= nil and seconds.week or
            limits.day ~= nil and seconds.day or
            limits.hour ~= nil and seconds.hour or
            seconds.minute

        local age = time - row[QUOTA.TIME]
        local expired = age > max
        -- print(limitType .. ',' .. age .. ',' .. max .. ',' .. tostring(expired))
        if expired then
            quota:delete(row[1])
        end
    end
end

function quotaGarbageCollectionFiber()
    while 0 == 0 do
        garbageCollection()
        fiber.sleep(seconds.minute) -- hour
    end
end
