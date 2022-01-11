import pytest
import os
from fastapi.exceptions import HTTPException
from server.main import get_system_root, walk_archive_paths


def test_get_system_root():
    assert (
        get_system_root("designsafe.storage.default")
        == "/corral-repl/tacc/NHERI/shared"
    )
    assert (
        get_system_root("designsafe.storage.community")
        == "/corral-repl/tacc/NHERI/community"
    )
    assert (
        get_system_root("designsafe.storage.published")
        == "/corral-repl/tacc/NHERI/published"
    )
    assert (
        get_system_root("project-7448086614930166251-242ac113-0001-012")
        == "/corral-repl/tacc/NHERI/projects/7448086614930166251-242ac113-0001-012"
    )
    with pytest.raises(HTTPException):
        get_system_root("not-a-real-system")


def test_walk_archive(tmp_path):
    """
    Generate and walk the following directory structure at tmp_path:
    .
    ├── f1.txt
    └── sub_path/
        ├── f2.txt
        └── sub_path2/
            └── f3.txt
    """
    base = tmp_path

    f1 = base / "f1.txt"
    f1.write_text("CONTENT 1")

    sub = base / "sub_path"
    os.mkdir(sub)
    f2 = sub / "f2.txt"
    f2.write_text("CONTENT 2")

    sub2 = sub / "sub_path2"
    os.mkdir(sub2)
    f3 = sub2 / "f3.txt"
    f3.write_text("CONTENT 3")

    requested_files = ["f1.txt", "sub_path"]
    walk_result = walk_archive_paths(base, requested_files)

    assert walk_result == [
        {"fs": str(base / "f1.txt"), "n": "f1.txt"},
        {"fs": str(base / "sub_path" / "f2.txt"), "n": "sub_path/f2.txt"},
        {
            "fs": str(base / "sub_path" / "sub_path2" / "f3.txt"),
            "n": "sub_path/sub_path2/f3.txt",
        },
    ]
