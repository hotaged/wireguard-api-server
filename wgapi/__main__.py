import asyncio
import typing
from os import environ, listdir
from fastapi.responses import FileResponse, UJSONResponse
from fastapi.requests import Request
from fastapi.exceptions import HTTPException
from fastapi import FastAPI, Header, Depends
from pydantic import BaseModel


config_path = environ.get('CONFIG_PATH')
secret_key = environ.get('SECRET_KEY')
debug = environ.get('DEBUG') == '1'

configuration = {}

if not debug:
    configuration.update({
       'docs_url': None,
       'redoc_url': None
    })


app = FastAPI(**configuration)


class XAPITokenVerification:
    def __init__(self, api_token: str):
        self.api_token = api_token

    async def __call__(self, x_api_token: str = Header()):
        if x_api_token != self.api_token:
            raise HTTPException(status_code=400, detail="X-API-TOKEN invalid.")


class Peer(BaseModel):
    config: str
    qrcode: str

    __all_peers__: dict = {}

    class InvalidView(Exception):
        def __init__(self, view: str):
            self.view = view

    @classmethod
    def create(cls, directory: str) -> 'Peer':
        cls.__all_peers__[directory] = cls(
            config=f'{config_path}/{directory}/{directory}.conf',
            qrcode=f'{config_path}/{directory}/{directory}.png'
        )
        return cls.get(directory)

    @classmethod
    def get(cls, directory: str) -> 'Peer':
        return cls.__all_peers__[directory]

    @classmethod
    def all(cls) -> list[str, ...]:
        return list(cls.__all_peers__.keys())

    def view(self, view: str) -> typing.Union[str, None]:
        if view not in ['config', 'qrcode']:
            raise self.InvalidView(view)

        return getattr(self, view)


@app.on_event('startup')
async def load_configs():
    # Waiting 10 seconds to let wireguard
    # server initialize properly
    await asyncio.sleep(10)

    def only_peers_filter(directory: str) -> bool:
        return directory.startswith('peer')

    for file in filter(only_peers_filter, listdir(config_path)):
        Peer.create(file)


@app.exception_handler(KeyError)
async def key_error_handler(*_) -> UJSONResponse:
    return UJSONResponse({'result': None, 'exception': 'Not found.'}, status_code=404)


@app.exception_handler(Peer.InvalidView)
async def peer_invalid_view_handler(_: Request, exception: Peer.InvalidView) -> UJSONResponse:
    return UJSONResponse({'result': None, 'exception': f'View: {exception.view} does not exists.'})


@app.get(
    "/configs",
    dependencies=(
        Depends(XAPITokenVerification(secret_key)),
    )
)
async def configs() -> list[str, ...]:
    return Peer.all()


@app.get(
    "/configs/{peer}/{view}",
    dependencies=(
        Depends(XAPITokenVerification(secret_key)),
    )
)
async def get_peer_config(peer: str, view: str) -> FileResponse:
    return FileResponse(Peer.get(peer).view(view))
