import json
import base64
import os
from werkzeug.test import Client, EnvironBuilder
from .common import ResponseWrapperBase

import logging
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
        """Override base supplying APIGateway response from WSGI response"""
        rd = {
            'statusCode': self.status_code,
            'headers': prepared_headers[0],
            'multiValueHeaders': prepared_headers[1],
            'isBase64Encoded': True
        }
        d = copy.deepcopy(rd)
        if prepared_body:
            rd['body'] = prepared_body
            d['body'] = (prepared_body[:20] + b'...'
                         if len(prepared_body) > 25
                         else prepared_body)
        logger.info(f'{__name__} response dict: {d!r}')
        if prepared_body:
            logger.debug(f'{__name__} ... Full body: {base64.b64decode(prepared_body)!r}')
        return rd

def wsgi_lambda_handler_APIGateway_common(app_object,
                                          event,
                                          context,
                                          method,
                                          query_string,
                                          headers,
                                          base_url,
                                          adjusted_path):
    saveLevel = set_level_for_apigateway_event(logger, event)
    logger.debug(f'{__name__} event: {json.dumps(event)}')

    data = None
    body = event.get('body')
    if body:
        data = base64.b64decode(body) if event.get('isBase64Encoded') else body
    if isinstance(data, bytes):
        data_present = data if len(data) < 20 else (data[:17] + b'...')
    elif isinstance(data, str):
        data_present = data if len(data) < 20 else (data[:17] + '...')
    elif isinstance(data, NoneType):
        data_present = None
    else:
        data_present = f'(unexpected type {type(data)})'
    logger.debug(f'{__name__} established body data:{data_present!r}, headers follow...')
    b = EnvironBuilder(
        path=adjusted_path,
        base_url=base_url,
        headers=headers,
        data=data,
        query_string=query_string,
        method=method)

    logger.debug(f'{__name__} environ: {b.get_environ()}')
    response = Client(app_object, ResponseWrapperAPIGateway).open(b).get_response()
    restore_level(logger, saveLevel)
    return response
