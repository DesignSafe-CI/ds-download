from server.main import get_base_path, walk_paths, TapisFile
import os


def test_get_base_path():
    assert (
        get_base_path("designsafe.storage.default", "/path/to/file")
        == "/corral-repl/tacc/NHERI/shared/path/to/file"
    )
    assert (
        get_base_path("designsafe.storage.default", "path/to/file")
        == "/corral-repl/tacc/NHERI/shared/path/to/file"
    )
    assert (
        get_base_path("designsafe.storage.community", "/path/to/file")
        == "/corral-repl/tacc/NHERI/community/path/to/file"
    )
    assert (
        get_base_path("designsafe.storage.published", "/path/to/file")
        == "/corral-repl/tacc/NHERI/published/path/to/file"
    )
    assert (
        get_base_path("project-7448086614930166251-242ac113-0001-012", "/path/to/file")
        == "/corral-repl/tacc/NHERI/projects/7448086614930166251-242ac113-0001-012/path/to/file"
    )


def test_walk_paths(tmp_path):
    base = tmp_path
    sub = base / "sub_path"
    os.mkdir(sub)

    f1 = base / "f1.txt"
    f1.write_text("CONTENT 1")

    f2 = sub / "f2.txt"
    f2.write_text("CONTENT 2")

    requested_files = [
        TapisFile(**{
            "path": "",
            "type": "folder"
        })
    ]

    paths2 = walk_paths(base, requested_files)
    assert paths2 == [
        {'fs': str(base / "f1.txt"), 'n': 'f1.txt'},
        {'fs': str(base / "sub_path" / "f2.txt"), 'n': "sub_path/f2.txt"}
    ]

