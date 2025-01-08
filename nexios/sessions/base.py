import typing
from nexios.config import get_config
from datetime import datetime
class BaseSessionInterface:

    modified = False

    accessed = False

    deleted = False

    _session_cache = {} 


    def __init__(self,session_key :str) -> None:
        
        config = get_config()
        self.session_key = session_key 
        assert config.secret_key != None, "Secret key is required to use session"
        self.config = config
        self.session_config = config.session




    def set_session(self,key :str,value :str):
        
        self.modified = True
        self.accessed = True
        print(self.modified)
        self._session_cache[key] = value
    
    def get_session(self, key):
        self.accessed = True
        
        return self._session_cache.get(key, None)
        

    def get_all(self):
        self.accessed = True
        return self._session_cache.items()
    
    def keys(self):
        return self._session_cache.keys()
    
    def values(self):
        return self._session_cache.items()
    
    def is_empty(self):
        return self._session_cache.items().__len__() == 0
    

    async def save(self):

        raise NotImplemented

    def get_cookie_name(self) -> str:
        """The name of the session cookie. Uses``app.config.SESSION_COOKIE_NAME``."""
        if not self.session_config:
            return "session_id"
        return self.session_config.session_cookie_name or "session_id"

    def get_cookie_domain(self) -> str | None:
        """Returns the domain for which the cookie is valid. Uses `config.SESSION_COOKIE_DOMAIN`."""
        if not self.session_config:
            return None
        return self.session_config.session_cookie_domain

    def get_cookie_path(self) -> str:
        """Returns the path for which the cookie is valid. Uses `config.SESSION_COOKIE_PATH`."""
        if not self.session_config:
            return None
        return self.session_config.session_cookie_path

    def get_cookie_httponly(self) -> bool:
        """Returns whether the session cookie should be HTTPOnly. Uses `session_config.session_cookie_httponly`."""
        if not self.session_config:
            return None
        return self.session_config.session_cookie_httponly

    def get_cookie_secure(self) -> bool:
        """Returns whether the session cookie should be secure. Uses `session_config.session_cookie_secure`."""
        if not self.session_config:
            return None
        return self.session_config.session_cookie_secure

    def get_cookie_samesite(self) -> str | None:
        """Returns the SameSite attribute for the cookie. Uses `session_config.session_cookie_samesite`."""
        if not self.session_config:
            return None
        return self.session_config.session_cookie_samesite

    def get_cookie_partitioned(self) -> bool:
        """Returns whether the cookie should be partitioned. Uses `session_config.session_cookie_partitioned`."""
        if not self.session_config:
            return None
        return self.session_config.session_cookie_partitioned

    def get_expiration_time(self) -> datetime | None:
        """Returns the expiration time for the session. Uses `self.session_config.session_expiration_time`."""
        if not self.session_config:
            return datetime.utcnow() +   86400
        if self.session_config.session_permanent:
            return datetime.utcnow() + self.session_config.session_expiration_time or 86400
        return None

    @property
    def should_set_cookie(self) -> bool:
        """Determines if the cookie should be set. Depends on `config.SESSION_REFRESH_EACH_REQUEST`."""
        print(self.modified)
        if not self.session_config:
            
            return self.modified
        return self.modified or (
            self.session_config.session_permanent and self.session_config.session_refresh_each_request
        )
        

    def has_expired(self) -> bool:
        """Returns True if the session has expired."""
        expiration_time = self.get_expiration_time()
        if expiration_time and datetime.utcnow() > expiration_time:
            return True
        return False
