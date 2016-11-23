function page_view(url, ip)
    print('page_view: ', url, ip)
    local pages = box.space.pages
    local upv = box.space.unique_page_views
    local res = pages.index.secondary:select{url}
    if #res > 0 then
      local tuple = res[1]
      local page_id = tuple[1]
      -- return false
      print('tuple found', tuple)
      local upv_res = upv:select{page_id, ip}
      print('upv_res', upv_res)
      if #upv_res > 0 then
          return tuple[3]
      else
          pages.index.secondary:update(url, {{'+', 3, 1}})
          upv:insert{page_id, ip}
          return tuple[3] + 1
      end
    else
      local res = pages:auto_increment{url, 1}
      print('new url', res)
      upv:insert{res[1], ip}
      return 1
    end
end
