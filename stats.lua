function store_ref(ref, url, ip, uid)
  if not ref or ref == '' then return nil end
  box.space.refs:auto_increment{ref, url, ip, uid, math.floor(fiber.time())}
end

function page_view(url, ip, uid, ref)
    local user_id = uid
    print('page_view: ', url, user_id, ref)
    local pages = box.space.pages
    local upv = box.space.unique_page_views
    local res = pages.index.secondary:select{url}
    if #res > 0 then
      local tuple = res[1]
      local page_id = tuple[1]
      -- return false
      print('tuple found', tuple)
      local upv_res = upv:select{page_id, user_id}
      print('upv_res', upv_res)
      if #upv_res > 0 then
          return tuple[3]
      else
          pages.index.secondary:update(url, {{'+', 3, 1}})
          upv:insert{page_id, user_id}
          store_ref(ref, url, ip, uid)
          return tuple[3] + 1
      end
    else
      local res = pages:auto_increment{url, 1}
      print('new url', res)
      upv:insert{res[1], user_id}
      store_ref(ref, url, ip, uid)
      return 1
    end
end
