from slowapi import Limiter
from slowapi.util import get_remote_address

def get_api_key_for_limit(request):
    return request.headers.get('X-API-Key') or get_remote_address(request)

limiter = Limiter(key_func=get_api_key_for_limit)
