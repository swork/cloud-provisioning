import base64
from .common import ResponseWrapperBase

import logging, os
logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LEVEL', logging.DEBUG)))

def set_level_for_apigateway_event(logger, event):
    level = (event.get('stageVariables') or {}).get('LEVEL')
    if level:
        saveLevel = logger.getLevel()
        logger.setLevel(level)
    else:
        saveLevel = None
    return saveLevel


def restore_level(logger, saveLevel):
    if saveLevel:
        logger.setLevel(saveLevel)

class ResponseWrapperAPIGateway(ResponseWrapperBase):
    """Match AWS Gateway API expectations. v2 accepts v1 response, so that's what
    we provide here."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def headers_from_wsgi(self):
        headers1 = {}
        headersN = {}
        headersCounter = {}
        wsgi_headers = self.headers.to_wsgi_list()
        for h in wsgi_headers:  # [(key, value), (key, value)] where key can repeat
            if h[0] in headers1:
                headersN.setdefault(h[0], []).append(h[1])
            else:
                headers1[h[0]] = h[1]
        for k in headersN.keys():
            del headers1[k]
        return (headers1, headersN)

    def body_from_wsgi(self):
        body = base64.b64encode(self.data)
        return body

    def response_dict(self, prepared_headers, prepared_body):
        trunc_body = (prepared_body[:20] + b'...'
                      if len(prepared_body) > 25
                      else prepared_body)
        d = {
            'statusCode': self.status_code,
            'body': trunc_body,
            'headers': prepared_headers[0],
            'multiValueHeaders': prepared_headers[1],
            'isBase64Encoded': True
        }
        logger.info(d)
        logger.debug(f'Full body: {self.body_from_wsgi()!r}')
        d['body'] = prepared_body
        return d


