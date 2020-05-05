# see __init__.py for note about environ context
import os
from werkzeug.datastructures import Headers
from .apigateway_common import wsgi_lambda_handler_APIGateway_common

import logging
logging.basicConfig(datefmt='')
logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LEVEL', logging.DEBUG)))

def wsgi_lambda_handler_APIGatewayv2(app_object, event, context):
    def werkzeug_headers_from_v2(h1):
        h = Headers()
        for k, v in h1.items():
            h.add(k.lower(), v)
        return h
    wzh = werkzeug_headers_from_v2(event.get('headers'))

    def _(event):
        epath = event['rawPath']
        rctx = event['requestContext']
        estage = rctx.get('stage')
        if estage and estage != '$default' and estage == epath[1:len(estage)+1]:
            maybe_slash_stage = '/' + estage
            adjusted_path = epath[len(estage)+1:]
        else:
            maybe_slash_stage = ''
            adjusted_path = epath
        return (f'http://{rctx["domainName"]}:443{maybe_slash_stage}',
                adjusted_path)
    base_url, adjusted_path  = _(event)

    return wsgi_lambda_handler_APIGateway_common(
        app_object, event, context,
        event['requestContext']['http']['method'],
        event['rawQueryString'],
        wzh,
        base_url,
        adjusted_path)

