from typing import List, Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.param_functions import Depends
from fastapi.responses import StreamingResponse
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


app = FastAPI()


class MessageReponse(BaseModel):
    message: str


@app.get("/", response_model=MessageReponse)
def read_root(request: Request):
    return {"message": f"Hello world, {request.client.host}"}


class TapisFile(BaseModel):
    path: str
    type: Literal["file", "folder"]


class ZipRequest(BaseModel):
    system: str
    path: str
    files: List[TapisFile]


def get_base_path(system: str, path: str):
    match system:
        case "designsafe.storage.default":
            root_dir = "/corral-repl/tacc/NHERI/shared"
        case "designsafe.storage.community":
            root_dir = "/corral-repl/tacc/NHERI/community"
        case "designsafe.storage.published":
            root_dir = "/corral-repl/tacc/NHERI/published"
        case prj_system if system.startswith("project-"):
            project_id = prj_system.split("-", 1)[1]
            root_dir = os.path.join("/corral-repl/tacc/NHERI/projects", project_id)

    return os.path.join(root_dir, path.strip("/"))


def walk_paths(base_path: str, files: List[TapisFile]):
    base = Path(base_path)
    paths = []
    size = 0
    for file in files:
        mount_path = base / file.path.strip("/")
        if file.type == "file":
            paths.append({"fs": str(mount_path), "n": mount_path.name})
        elif file.type == "folder":
            for file_path in filter(lambda f: f.is_file(), mount_path.glob("**/*")):
                paths.append(
                    {"fs": str(file_path), "n": str(file_path.relative_to(mount_path))}
                )
                size += file_path.stat().st_size
                if size > 2e9:
                    raise HTTPException(
                        status_code=413, detail="Archive size limited to 2Gb."
                    )

    return paths


class CheckResponse(BaseModel):
    key: str


@app.put("/check", response_model=CheckResponse)
def check_downloadable(
    request: ZipRequest,
    auth: http.HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    PUBLIC_SYSTEMS = ["designsafe.storage.community", "designsafe.storage.published"]
    if request.system not in PUBLIC_SYSTEMS:

        # Limit API to public systems for initial release.
        raise HTTPException(
            status_code=403, detail="Private systems are currently disabled."
        )
        """
        if not auth:
            raise HTTPException(
                status_code=401,
                detail="Attempt to access private resource without auth credentials.",
            )
        try:
            listing_url = (
                f"{TAPIS_BASE_URL}"
                "/files/v2/listings/system/"
                f"{request.system}/{request.path.strip('/')}"
            )
            resp = requests.get(
                listing_url, headers={"Authorization": f"Bearer {auth.credentials}"}
            )
            resp.raise_for_status()
            return {"message": "success"}
        except HTTPError:
            print(resp.content)
            raise HTTPException(status_code=403, detail=resp.json())
        """
    base_path = get_base_path(request.system, request.path)
    paths = walk_paths(base_path, request.files)

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

    paths = json.loads(key_json)
    r.delete(key)

    zfly = zipfly.ZipFly(paths=paths)
    generator = zfly.generator()
    return StreamingResponse(
        generator,
        headers={"Content-Disposition": "attachment; filename=download.zip"},
        media_type="application/octet-stream",
    )
