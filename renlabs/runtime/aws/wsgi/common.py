from werkzeug.wrappers import BaseResponse

class ResponseWrapperBase(BaseResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def headers_from_wsgi(self):
        raise RuntimeError("To be overridden in subclass")

    def body_from_wsgi(self):
        raise RuntimeError("To be overridden in subclass")

    def response_dict(self, prepared_headers, prepared_body):
        raise RuntimeError("To be overridden in subclass")

    def get_response(self):
        response_dict = self.response_dict(
            prepared_headers=self.headers_from_wsgi(),
            prepared_body=self.body_from_wsgi())
        return response_dict

