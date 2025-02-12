from nexios.middlewares.base import BaseMiddleware
from .signed_cookies import SignedSessionManager
from .file import FileSessionManager
from .base import BaseSessionInterface
from nexios.http import Request,Response
from nexios.config import get_config
import warnings,typing
class SessionMiddleware(BaseMiddleware):

    async def process_request(self, request :Request, response :Response,call_next:  typing.Callable[..., typing.Awaitable[typing.Any]]):
    
        self.config = get_config().session 
        if not self.config:
            warnings.warn(
            " Warning: secret_key is not set! Sessions will not be used. "
            "Set a secret_key to enable secure session handling.",
            RuntimeWarning
            )
            await call_next()
            return
        if self.config:
            session_cookie_name = self.config.session_cookie_name
        else:
            session_cookie_name =  "session_id"

        self.session_cookie_name = session_cookie_name
        managers :typing.Dict[str,typing.Any]= {
            "file":FileSessionManager,
            "cookies":SignedSessionManager
        }    
        if self.config:
            manager_config = self.config.session_manager 
        else:
            manager_config  = "cookies"
        
        manager :BaseSessionInterface = managers.get(manager_config,SignedSessionManager)
        session :typing.Type[BaseSessionInterface] = manager(session_key=request.cookies.get(session_cookie_name)) #type:ignore
        await session.load() #type: ignore
        request.scope['session'] = session
        await call_next()
        

    async def process_response(self, request :Request , response :Response):
        if not self.config:
            warnings.warn(
            " Warning: secret_key is not set! Sessions will not be used. "
            "Set a secret_key to enable secure session handling.",
            RuntimeWarning
            )
            return 
        if request.session.is_empty() and request.session.accessed:
            response.delete_cookie(
                key= self.session_cookie_name
                
                )
            return 
        
        if request.session.should_set_cookie:
            await request.session.save()

            session_key = request.session.get_session_key()

            response.set_cookie(
                key =  self.session_cookie_name,
                value=session_key,
                domain=request.session.get_cookie_domain(),
                path=request.session.get_cookie_path(),
                httponly=request.session.get_cookie_httponly(),
                secure=request.session.get_cookie_secure(),
                samesite=request.session.get_cookie_samesite(),
                expires=request.session.get_expiration_time()
                
            )
        

