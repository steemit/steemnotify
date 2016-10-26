require 'table_utils'

-- NTYPES = {
--   'total': 0,
--   'feed': 1,
--   'reward': 2,
--   'transfer': 3,
--   'mention': 4,
--   'follow': 5,
--   'vote': 6,
--   'comment_reply': 7,
--   'post_reply': 8,
--   'key_update': 9,
--   'message': 10
-- }

function notification_add(account, ntype)
  -- print('notification_push -->', account, ntype)
  local space = box.space.notifications
  local res = space:select{account}
  if #res > 0 then
    -- print_r(res)
    local tuple = res[1]
    -- print('existing:', tuple)
    return space:update(account, {{'+', 2, 1}, {'+', ntype + 2, 1}})
  else
    local tuple = {account, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
    tuple[ntype + 2] = 1;
    -- print('new:')
    -- print_r(tuple)
    return space:insert(tuple)
  end
end

function notification_read(account, ntype)
  -- print('notification_read -->', account, ntype)
  local space = box.space.notifications
  local res = space:select{account}
  if #res == 0 then return nil end
  local tuple = res[1]
  local count = tuple[ntype + 2]
  if count == nil or count <= 0 then return tuple end
  local res = space:update(account, {{'-', 2, count}, {'=', ntype + 2, 0}})
  return res
end

function add_follower(account, follower)
  local space = box.space.followers
  local res = space:select({account})
  if #res == 0 then return nil end
  local followers = res[1][2]
  if not contains(followers, follower) then
    table.insert(followers, #followers+1, follower)
    space:update(account, {{'=', 2, followers}})
  end
  return true
end
