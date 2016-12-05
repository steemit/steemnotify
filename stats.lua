function store_ref(ref, page_id, ip, uid)
  if not ref or ref == '' then return nil end
  local pages = box.space.pages
  local ref_page_id
  local res = pages.index.secondary:select{ref}
  if #res > 0 then
    ref_page_id = res[1][1]
    pages.index.secondary:update(ref, {{'+', 3, 1}})
  else
    local ref_page_res = pages:auto_increment{ref, 1}
    ref_page_id = ref_page_res[1]
  end
  box.space.refs:auto_increment{ref_page_id, page_id, ip, uid, math.floor(fiber.time())}
end

function page_view(url, ip, uid, ref)
    local user_id = uid
    -- print('page_view: ', url, user_id, ref)
    local pages = box.space.pages
    local upv = box.space.unique_page_views
    local res = pages.index.secondary:select{url}
    local current_time = math.floor(fiber.time())
    if #res > 0 then
      local tuple = res[1]
      -- print('tuple found', res)
      local page_id = tuple[1]
      local upv_res = upv:select{page_id, user_id}
      -- print('upv_res', upv_res)
      if #upv_res > 0 then
          return {false, tuple[3]}
      else
          pages.index.secondary:update(url, {{'+', 3, 1}})
          upv:insert{page_id, user_id, current_time}
          upv:insert{page_id, ip, current_time}
          store_ref(ref, page_id, ip, uid)
          return {true, tuple[3] + 1}
      end
    else
      res = pages:auto_increment{url, 1}
      local page_id = res[1]
      -- print('new url', res)
      upv:insert{page_id, user_id, current_time}
      upv:insert{page_id, ip, current_time}
      store_ref(ref, page_id, ip, uid)
      return {true, 1}
    end
end

function get_page_refs(url)
  local res = {}
  local pages = box.space.pages
  local refs = box.space.refs
  local page_res = pages.index.secondary:select{url}
  if #page_res == 0 then return nil end
  local page_id = page_res[1][1]
  local refs_res = refs.index.by_page:select{page_id}
  for i, row in pairs(refs_res) do
    local ref_page_id = row[2]
    ref_page = pages:select{ref_page_id}
    if #ref_page > 0 then
      local page = ref_page[1][2]
      if res[page] then
        res[page] = res[page] + 1
      else
        res[page] = 1
      end
    end
  end
  return res
end
