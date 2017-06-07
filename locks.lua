function lock_entity(entity_name)
    local space = box.space.locks
    local res = space:select{entity_name}
    local current_time = math.floor(fiber.time())
    if #res > 0 then
      local tuple = res[1]
      local lock_time = tuple[2]
      if current_time - lock_time < 30 then
        return false
      else
        space:update(entity_name, {{'=', 2, current_time}})
      end
      return true
    else
      local tuple = {entity_name, current_time}
      space:insert(tuple)
      return true
    end
end

function unlock_entity(entity_name)
    local space = box.space.locks
    return space:delete{entity_name}
end
