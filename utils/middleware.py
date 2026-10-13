import threading

_thread_locals = threading.local()

def get_current_request():
    """Retrieve the current active request from thread-local storage."""
    return getattr(_thread_locals, 'request', None)

class CurrentRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            del _thread_locals.request