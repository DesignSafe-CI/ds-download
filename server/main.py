import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import time


def slow_numbers(minimum, maximum):
    yield('<html><body><ul>')
    for number in range(minimum, maximum + 1):
        yield '<li>%d</li>' % number
        time.sleep(0.5)
    yield('</ul></body></html>')


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello world."}


@app.get("/download")
def download_file():
    generator = slow_numbers(1, 10)

    return StreamingResponse(
        generator,
        headers={"Content-Disposition": "attachment; filename=download.txt"},
        media_type="application/octet-stream",
    )
