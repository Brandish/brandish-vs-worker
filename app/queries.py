SELECT_ITEMS = """
SELECT    id, waywire_id, url, source 
FROM      item_item;
"""


SELECT_ITEM = """
SELECT id, waywire_id
FROM   item_item
WHERE  id = %(item_id)s;
"""

BULK_UPDATE_ITEMS = """
SELECT * FROM update_items(%s::json);
"""

BULK_UPDATE_ITEM_VIEW_COUNT = """
UPDATE item_item 
    SET view_count = %(view_count)s,
        waywire_video_id = %(waywire_video_id)s,
        external_video_id = %(external_video_id)s,
        external_video_url = %(external_video_url)s
WHERE id = %(id)s
"""