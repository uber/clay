from flask import request
from clay import app, config
import json

log = config.get_logger('clay.docs')


def parse_docstring_param(directive, key, value):
    p = {
        'name': key,
        'description': value.split('{', 1)[0],
        'required': False,
        'dataType': 'string',
        'type': 'primitive',
        'allowMultiple': False,
    }
    if '{' in value and '}' in value:
        p.update(json.loads(value[value.find('{'):value.find('}')]))

    if directive == 'json':
        directive = 'body'
        p['type'] = 'complex'

    if directive in ('query', 'body', 'path', 'form'):
        p['paramType'] = directive
    elif directive == 'reqheader':
        p['paramType'] = 'header'
    else:
        log.warning('Ignoring unknown docstring param %s', directive)
        return
    return p


def parse_docstring(docstring):
    '''
    Turns autodoc http dialect docstrings into swagger documentation
    '''
    if not docstring:
        return
    
    params = []
    responses = []
    stripped = ''
    rtype = None
    for line in docstring.split('\n'):
        line = line.lstrip('\t ')
        if not line.startswith(':'):
            stripped += line + '\n<br />'
            continue
        
        directive, value = line.split(':', 2)[1:]
        value = value.strip('\t ')

        directive = directive.split(' ', 1)
        if len(directive) > 1:
            directive, key = directive
        else:
            directive = directive[0]
            key = None

        if directive in ('json', 'body', 'query', 'path', 'form', 'reqheader'):
            param = parse_docstring_param(directive, key, value)
            if param:
                params.append(param)
            continue

        if directive == 'status':
            responses.append({
                'code': int(key),
                'message': value,
            })
            continue
        
        if directive == 'rtype':
            rtype = value
        log.warning('Ignoring unknown docstring param %s', directive)

    return (params, responses, stripped, rtype)


def get_model(modelspec):
    module, name = modelspec.rsplit('.', 1)
    module = __import__(module)
    return {
        'id': modelspec,
        'properties': getattr(module, name),
    }


@app.route('/_docs', methods=['GET'])
def clay_docs():
    '''
    Returns a JSON document describing this service's API

    Endpoints are inferred from routes registered with Flask and the docstrings
    bound to those methods.

    Dialect documentation http://pythonhosted.org/sphinxcontrib-httpdomain/
    Swagger documentation https://github.com/wordnik/swagger-core/wiki

    :status 200: Generated swagger documentation
    :status 500: Something went horribly wrong
    '''
    headers = {'Content-type': 'application/json'}
    response = {
        'apiVersion': '0.2',
        'swaggerVersion': '1.2',
        'basePath': config.get('docs.base_path', None) or request.url_root.rstrip('/'),
        'resourcePath': '/',
        'apis': [],
        'models': {},
    }

    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue

        api = {
            'path': rule.rule,
            'operations': [],
        }
        view_func = app.view_functions[rule.endpoint]
        if view_func.__doc__:
            docstring = view_func.__doc__.strip('\r\n\t ')
            params, responses, stripped_docstring, rtype = parse_docstring(docstring)

            shortdoc = [x for x in docstring.split('\n') if x]
            if not shortdoc:
                shortdoc = 'Undocumented'
            else:
                shortdoc = shortdoc[0]
        else:
            shortdoc = 'Undocumented'
            params = []
            responses = []
            stripped_docstring = shortdoc
            rtype = None


        for http_method in rule.methods:
            if http_method in ('HEAD', 'OPTIONS'):
                continue
            doc = {
                'method': http_method,
                'nickname': view_func.__name__,
                'summary': shortdoc,
                'notes': stripped_docstring,
                'parameters': params,
                'responseMessage': responses,
            }
            if rtype:
                doc['responseClass'] = rtype
                model = get_model(rtype)
                response['models'][rtype] = model

            api['operations'].append(doc)
        response['apis'].append(api)

    return (json.dumps(response, indent=2), 200, headers)
