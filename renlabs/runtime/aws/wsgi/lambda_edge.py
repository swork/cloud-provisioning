# see __init__.py for note about environ context
import logging, os
logging.basicConfig(datefmt='')
logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LEVEL', logging.DEBUG)))

import werkzeug.datastructures
from .common import ResponseWrapperBase

class ResponseWrapperLambdaAtEdge(ResponseWrapperBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def headers_from_wsgi(self):
        """want {'content-type': [{ 'key': 'Content-Type', 'value': '' }], ... }"""
        headers = {}
        wsgi_headers = self.headers.to_wsgi_list()
        for h in wsgi_headers:  # [(key, value), (key, value)] where key can repeat
            key = h[0]
            item = {
                    'key': key,
                    'value': h[1]
            }
            klower = key.lower()
            if klower in headers:
                headers[klower].append(item)
            else:
                headers[klower] = [item]
        return headers

    def body_from_wsgi(self):
        body = base64.b64encode(self.data)
        return body

    def response_dict(self, prepared_headers, prepared_body):
        """Override providing a Lambda@Edge response from WSGI response"""
        trunc_body = (prepared_body[:20] + b'...'
                      if len(prepared_body) > 25
                      else prepared_body)
        d = {
            'status': self.status_code,  # statusDescription not req'd per docs
            'body': trunc_body,
            'bodyEncoding': 'base64',
            'headers': prepared_headers,
        }
        logger.info(d)
        logger.debug('Full body:', repr(prepared_body))
        d['body'] = prepared_body
        return d

def wsgi_lambda_handler_LambdaAtEdge_origin(app_object, event, context):
    logger.debug(f'event: {json.dumps(event)}')
    r = event['Records']
    if len(r) != 1:
        raise RuntimeError("Unexpected count of Records in event, not 1")
    cf = r[0]['cf']
    if 'response' in cf:
        raise RuntimeError("WSGI install is only appropriate on ...Request triggers, not ...Response")
    req = cf['request']

    def werkzeug_headers_from_cloudfront(cf_headers):
        h = werkzeug.datastructures.Headers()
        for lowerkey, hobj in cf_headers.items():
            for k, v in hobj.items():
                h.add(lowerkey, v)
        return h
    wzh = werkzeug_headers_from_cloudfront(req['headers'])

    def divide_base_from_full_path(uri):
        env_base = os.environ.get('BASE_PATH', '')
        if env_base and env_base[0] != '/':
            env_base = '/' + env_base
        if ev_base[-1] == '/':
            env_base = env_base[:-1]
        if env_base:
            eblen = len(env_base)
            if env_base == uri[:eblen]:
                return env_base, uri[eblen:]
        return '', uri
    base_path, path = divide_base_from_full_path(req['uri'])

    base_url = f'http://{wzh["host"]}/{base_path}'
    b = EnvironBuilder(
        path=path,
        base_url=base_url,
        headers=wzh.to_wsgi_list(),
        query_string=req.get('querystring') or '',
        method=req['method'])
    logger.debug(f'cf environ: {b.get_environ()}')
    response = Client(app_object, ResponseWrapperAPIGateway).open(b).get_response()

    return response


def wsgi_lambda_handler_LambdaAtEdge_viewer(app_object, event, context):
    return wsgi_lambda_handler_LambdaAtEdge_origin(app_object, event, context)


def wsgi_lambda_handler_LambdaAtEdge(app_object, event, context):
    return wsgi_lambda_handler_LambdaAtEdge_origin(app_object, event, context)

