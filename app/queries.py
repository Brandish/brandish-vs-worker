SELECT_ITEMS = """
SELECT id, waywire_id, url, source 
FROM   item_item ORDER BY view_count ASC LIMIT 2000;
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
    SET view_count = %(view_count)s
WHERE id = %(id)s
"""