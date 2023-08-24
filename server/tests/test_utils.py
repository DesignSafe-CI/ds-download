import pytest
import os
from fastapi.exceptions import HTTPException
from unittest.mock import MagicMock, create_autospec
from server.main import get_system_root, walk_archive_paths, check_system_access


def test_get_system_root():
    assert (
        get_system_root("designsafe.storage.default")
        == "/ds-mydata"
    )
    assert (
        get_system_root("designsafe.storage.community")
        == "/corral-repl/tacc/NHERI/community"
    )
    assert (
        get_system_root("designsafe.storage.published")
        == "/corral-repl/tacc/NHERI/published"
    )
    assert get_system_root("nees.public") == "/corral-repl/tacc/NHERI/public/projects"
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


def test_walk_archive_404(tmp_path):
    base = tmp_path
    with pytest.raises(HTTPException):
        walk_archive_paths(base, ["nonexistent_file.txt"])


@pytest.fixture
def mock_get_success(monkeypatch, request):
    import requests

    mock_fn = create_autospec(requests.get)
    mock_response = requests.Response()
    mock_response.status_code = 200

    mock_fn.return_value = mock_response
    monkeypatch.setattr(requests, "get", mock_fn)
    yield mock_fn


@pytest.fixture
def mock_get_error(monkeypatch):
    import requests

    mock_fn = create_autospec(requests.get)
    mock_response = requests.Response()
    mock_response.status_code = 404

    mock_fn.return_value = mock_response
    monkeypatch.setattr(requests, "get", mock_fn)
    yield mock_fn


def test_check_system_access_success(mock_get_success, monkeypatch):
    from server import main

    monkeypatch.setattr(main, "TAPIS_BASE_URL", "tapis.test")
    try:
        check_system_access(
            "test.system", ["/tmp/file1.txt", "/tmp/tmp2/file2.txt"], "ABC123"
        )
    except Exception:
        assert 0

    mock_get_success.assert_called_with(
        "tapis.test/files/v2/listings/system/test.system/tmp/?limit=1",
        headers={"Authorization": f"Bearer {'ABC123'}"},
    )


def test_check_system_access_failure(mock_get_error, monkeypatch):
    from server import main

    monkeypatch.setattr(main, "TAPIS_BASE_URL", "tapis.test")
    with pytest.raises(HTTPException):
        check_system_access(
            "test.system", ["/tmp/file1.txt", "/tmp/tmp2/file2.txt"], "ABC123"
        )

    mock_get_error.assert_called_with(
        "tapis.test/files/v2/listings/system/test.system/tmp/?limit=1",
        headers={"Authorization": f"Bearer {'ABC123'}"},
    )
