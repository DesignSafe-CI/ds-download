from typing import List, TypedDict, Annotated
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.param_functions import Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, http
from pydantic import BaseModel
from requests.models import HTTPError
import zipfly
import redis
import json
import os
from pathlib import Path
from uuid import uuid4
import requests

r = redis.Redis(host="ds_download_redis", port=6379, db=0)
TAPIS_BASE_URL = "https://agave.designsafe-ci.org"
TAPIS_V3_BASE_URL = "https://designsafe.tapis.io"


app = FastAPI()


class MessageReponse(BaseModel):
    message: str


@app.get("/", response_model=MessageReponse)
def read_root(request: Request):
    return {"message": f"Hello world, {request.client.host}"}


def get_system_root(system: str) -> str:
    match system:
        case "designsafe.storage.default":
            root_dir = "/ds-mydata"
        case "designsafe.storage.frontera.scratch":
            root_dir = "/frontera-scratch"
        case "designsafe.storage.frontera.work":
            root_dir = "/frontera-work"
        case "designsafe.storage.community":
            root_dir = "/corral-repl/tacc/NHERI/community"
        case "designsafe.storage.published":
            root_dir = "/corral-repl/tacc/NHERI/published"
        case "nees.public":
            root_dir = "/corral-repl/tacc/NHERI/public/projects"
        case prj_system if system.startswith("project-"):
            project_id = prj_system.split("-", 1)[1]
            root_dir = os.path.join("/corral-repl/tacc/NHERI/projects", project_id)
        case _:
            raise HTTPException(status_code=404, detail="Invalid storage system ID.")

    return root_dir


def raise_for_size(size: int, max_size: int = 2e9) -> None:
    if size > max_size:
        raise HTTPException(status_code=413, detail="Archive size is limited to 2Gb.")


class Archive(TypedDict):
    fs: str  # Represents the absolute path to a file on the host machine.
    n: str  # Represents the path to a file within the zip archive.


def walk_archive_paths(base_path: str, file_paths: List[str]) -> List[Archive]:
    base = Path(base_path)
    zip_paths = []
    size = 0
    for file in file_paths:
        full_path = base / file.strip("/")

        if full_path.is_file():
            zip_paths.append({"fs": str(full_path), "n": full_path.name})
            size += full_path.stat().st_size
            raise_for_size(size)

        elif full_path.is_dir():
            for file_path in filter(lambda f: f.is_file(), full_path.glob("**/*")):
                zip_paths.append(
                    {
                        "fs": str(file_path),
                        "n": str(file_path.relative_to(full_path.parent)),
                    }
                )
                size += file_path.stat().st_size
                raise_for_size(size)
        else:
            # No file/folder exists at the requested path, so raise a 404.
            raise HTTPException(
                status_code=404,
                detail="One or more of the requested files could not be found.",
            )

    return zip_paths


def check_system_access(system: str, paths: List[str], token: str) -> None:
    """
    Confirm a user's READ access to files in a system by using their Tapis access token
    to perform a listing at the files' common path.
    """

    common_path = os.path.commonpath(map(lambda p: p.strip("/"), paths))
    if common_path == "" and not system.startswith("project-"):
        raise HTTPException(
            status_code=403,
            detail="Detected a possible attempt to access multiple home directories.",
        )
    listing_url = (
        f"{TAPIS_BASE_URL}"
        "/files/v2/listings/system/"
        f"{system}/{common_path}/?limit=1"
    )
    try:
        resp = requests.get(listing_url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
    except HTTPError:
        raise HTTPException(status_code=resp.status_code, detail=resp.reason)
    

def check_system_access_v3(system: str, paths: List[str], token: str) -> None:
    """
    Confirm a user's READ access to files in a system by using their Tapis access token
    to perform a listing at the files' common path.
    """

    common_path = os.path.commonpath(map(lambda p: p.strip("/"), paths))
    if common_path == "" and not system.startswith("project-"):
        raise HTTPException(
            status_code=403,
            detail="Detected a possible attempt to access multiple home directories.",
        )
    listing_url = (
        f"{TAPIS_V3_BASE_URL}"
        "/v3/files/ops/"
        f"{system}/{common_path}/?limit=1"
    )
    try:
        resp = requests.get(listing_url, headers={"x-tapis-token": token})
        resp.raise_for_status()
    except HTTPError:
        raise HTTPException(status_code=resp.status_code, detail=resp.reason)


class CheckResponse(BaseModel):
    key: str


class CheckRequest(BaseModel):
    system: str
    paths: List[str]


@app.put("/check", response_model=CheckResponse)
def check_downloadable(
    request: CheckRequest,
    x_tapis_token: Annotated[str | None, Header()] = None,
    auth: http.HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    PUBLIC_SYSTEMS = [
        "designsafe.storage.community",
        "designsafe.storage.published",
        "nees.public",
    ]
    if not (auth or x_tapis_token) and request.system not in PUBLIC_SYSTEMS:
        raise HTTPException(
            status_code=401,
            detail="This resource cannot be accessed without Tapis credentials.",
        )
    elif request.system not in PUBLIC_SYSTEMS:
        if x_tapis_token:
            check_system_access_v3(request.system, request.paths, x_tapis_token)
        else:
            check_system_access(request.system, request.paths, auth.credentials)

    system_root = get_system_root(request.system)
    paths = walk_archive_paths(system_root, request.paths)

    key = str(uuid4())
    r.set(key, json.dumps(paths))
    r.expire(key, 60)

    return {"key": key}


@app.get(
    "/download/{key}",
    openapi_extra={
        "responses": {
            200: {"content": {"application/octet-stream": {}, "application/zip": {}}}
        }
    },
)
def download_file(key: str):
    key_json = r.get(key)

    if not key_json:
        raise HTTPException(status_code=404, detail="Invalid download link.")

    paths: List[Archive] = json.loads(key_json)
    r.delete(key)

    if len(paths) == 1:
        # If there's only 1 file to return, download it directly instead of zipping it.
        return FileResponse(
            paths[0]["fs"],
            headers={"Content-Disposition": f"attachment; filename={paths[0]['n']}"},
        )

    zfly = zipfly.ZipFly(paths=paths)
    generator = zfly.generator()
    return StreamingResponse(
        generator,
        headers={"Content-Disposition": "attachment; filename=download.zip"},
        media_type="application/zip",
    )
