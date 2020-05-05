# see __init__.py for note about environ context
import os
import base64
import logging
logging.basicConfig(datefmt='')
logger = logging.getLogger(__name__)
logger.setLevel(int(os.environ.get('LEVEL', logging.DEBUG)))

from .apigateway_common import (
    set_level_for_apigateway_event,
    restore_level,
    ResponseWrapperAPIGateway,
    wsgi_lambda_handler_APIGateway_common)
from werkzeug.test import Client, EnvironBuilder
from werkzeug.datastructures import Headers

def wsgi_lambda_handler_APIGatewayv1(app_object, event, context):
    def qs(qsp, mvqsp):
        out = []
        for k in mvqsp:
            out.append((k, ','.join(mvqsp[k])))
        for k in qsp:
            if k not in mvqsp:
                out.append((k, qsp[k]))
        return '&'.join(map(lambda x: '='.join(x) if len(x) > 1 else x[0], out))
    query_string = qs(event.get('queryStringParameters') or {},
                      event.get('multiValueQueryStringParameters') or {})

    def werkzeug_headers_from_v1(h1, hN):
        h = werkzeug.datastructures.Headers()
        for k, vv in hN.items:
            for v in vv:
                h.add(k.lower(), v)
        for k, v in h1.items():
            h.add(k.lower(), v)  # docs unclear; repeating should be okay
        return h
    wzh = werkzeug_headers_from_v1(event.get('headers'), event.get('multiValueHeaders'))

    def _(event):
        rctx = event['requestContext']
        epath = rctx['path']
        estage = rctx.get('stage')
        if estage and estage != '$default' and estage == epath[1:len(estage)+1]:
            maybe_slash_stage = f'/{estage}'
            adjusted_path = epath[len(estage)+1:]
        else:
            maybe_slash_stage = ''
            adjusted_path = epath
        return (f'http://{rctx["domainName"]}:443{maybe_slash_stage}',
                adjusted_path)
    base_url, adjusted_path  = _(event)

    return wsgi_lambda_handler_APIGateway_common(
        app_object, event, context,
        event['httpMethod'],
        query_string,
        wzh,
        base_url,
        adjusted_path)

