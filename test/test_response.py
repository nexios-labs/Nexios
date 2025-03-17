from nexios import get_application,NexiosApp
import pytest
from nexios.http import Request,Response
from nexios.testing import Client
import datetime as dt
import time
app :NexiosApp = get_application()
@app.get("/response/text")
async def send_text_response(req: Request, res :Response):
    return res.text("Hello from nexios")

@app.get("/response/bytes")
async def send_byes_response(req: Request, res :Response):
    return res.resp(b"XXXX",content_type="image/png")

@app.get("/response/json-none")
async def send_json_none_response(req: Request, res :Response):
    return res.json(None) #type:ignore

@app.get("/response/redirect")
async def send_redirect_response(req: Request, res :Response):
    return res.redirect("http://google.com")
import anyio


@app.get("/response/stream")
async def send_streaming_response(req: Request, res :Response):

    async def numbers(minimum: int, maximum: int):
        # async with lock:
        for i in range(minimum, maximum + 1):
            yield str(f"{i}, ")
            
            await anyio.sleep(0)
    generator = numbers(1, 5)
    return res.stream(generator) #type: ignore


@app.get("/response/headers")
async def send_header_response(req: Request, res :Response):
    headers = {"x-header-1": "123", "x-header-2": "456"}
    return res.json(None, headers=headers) #type:ignore


    


@app.get("/response/files")
async def send_file_response(req: Request, res :Response):
    res.file("C:/Users/dunamix/Documents/Nexios/test/static/example.txt",content_disposition_type="attachment")
    
    
@app.get("/response/cookies")
async def send_cookie_response(req: Request, res :Response):
    res.set_cookie(
            "mycookie", 
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
    res.text("cookie set")
    
@pytest.fixture(autouse=True)
async def async_client():
    async with  Client(app,log_requests=True) as c:
        yield c 
        
        
async def test_text_response(async_client :Client):
    response  = await async_client.get("/response/text")
    assert response.text == "Hello from nexios"
    assert response.status_code == 200
    
    
async def test_byte_response(async_client :Client):
    response  = await async_client.get("/response/bytes")
    assert response.content == b"XXXX"
    assert response.status_code == 200
    
async def test_json_none_response(async_client :Client):
    response  = await async_client.get("/response/json-none")
    assert response.json () is None
    assert response.status_code == 200 
    
    
async def test_redirect_response(async_client :Client):
    response  = await async_client.get("/response/redirect")
    assert response.url == "http://google.com"
    
    
    
async def test_streaming_response(async_client :Client):
    response  = await async_client.get("/response/stream")
    print(response)
    assert response.text == "1, 2, 3, 4, 5, "
    
    
async def test_response_with_header(async_client :Client):
    response = await async_client.get("/response/headers")
    assert response.headers["x-header-1"] == "123"
    assert response.headers["x-header-2"] == "456"
    

async def test_file_response(async_client :Client):
    response = await async_client.get("/response/files")
    assert response.status_code == 200
    expected_disposition = 'attachment; filename="example.txt"'
    assert response.headers["content-disposition"] == expected_disposition
    assert "content-length" in response.headers
    


async def test_file_response_range(async_client: Client):
    response = await async_client.get("/response/files", headers={"Range": "bytes=12-19"})
    assert response.status_code == 206
    assert response.headers["content-length"] == "8"
    
    




async def test_set_cookies(async_client :Client, monkeypatch :pytest.MonkeyPatch):
    mocked_now = dt.datetime(2037, 1, 22, 12, 0, 0, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(time, "time", lambda: mocked_now.timestamp())
    response = await async_client.get("/response/cookies")
    assert response.text == "cookie set"
    assert (
        response.headers["set-cookie"] == "mycookie=myvalue; Domain=localhost; expires=Thu, 22 Jan 2037 12:00:10 GMT; "
        "HttpOnly; Max-Age=10; Path=/; SameSite=none; Secure"
    )
