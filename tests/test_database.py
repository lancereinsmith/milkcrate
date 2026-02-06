from database import (
    delete_app,
    get_all_apps,
    get_app_by_container_id,
    get_app_by_id,
    insert_app,
    set_app_public,
    update_app_status,
)


def test_crud_flow(flask_app):
    with flask_app.app_context():
        insert_app("demo", "cid123", "image:tag", "/demo", 8000, is_public=False)

        apps = get_all_apps()
        assert len(apps) == 1

        app_row = apps[0]
        app_id = app_row["app_id"]

        # get by id
        fetched = get_app_by_id(app_id)
        assert fetched is not None

        # get by container id
        fetched2 = get_app_by_container_id("cid123")
        assert fetched2 is not None

        update_app_status(app_id, "running")
        refetched = get_app_by_id(app_id)
        assert refetched["status"].lower() == "running"

        set_app_public(app_id, True)
        refetched2 = get_app_by_id(app_id)
        assert int(refetched2["is_public"]) == 1

        delete_app(app_id)
        assert get_app_by_id(app_id) is None
