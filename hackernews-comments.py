# ---
# name: hackernews-comments
# deployed: true
# title: Hacker News Comments
# description: Returns the the Hacker News comments matching the search term
# params:
#   - name: properties
#     type: array
#     description: The properties to return, given as a string or array; defaults to all properties; see "Returns" for available properties
#     required: false
#   - name: filter
#     type: array
#     description: Search query to determine the rows to return, given as a string or array
#     required: false
# returns:
#   - name: title
#     type: string
#     description: The title of the story
#   - name: url
#     type: string
#     description: The url of the story
#   - name: author
#     type: string
#     description: The user who made the comment
#   - name: comment
#     type: string
#     description: The comment text
#   - name: parent_id
#     type: string
#     description: The parent id
#   - name: created_at
#     type: string
#     description: The date the story was created
# examples:
#   - '"*", "microsoft"'
#   - '"*", "google"'
# ---

import json
import urllib
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import itertools
from datetime import *
from decimal import *
from cerberus import Validator
from collections import OrderedDict

# main function entry point
def flexio_handler(flex):

    # get the input
    input = flex.input.read()
    input = json.loads(input)
    if not isinstance(input, list):
        input = []

    # define the expected parameters and map the values to the parameter names
    # based on the positions of the keys/values
    params = OrderedDict()
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': '*'}
    params['filter'] = {'required': False, 'type': 'string', 'default': ''} # placeholder to match form of index-styled functions
    params['config'] = {'required': False, 'type': 'string', 'default': ''} # index-styled config string
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    v = Validator(params, allow_unknown = True)
    params = v.validated(input)
    if params is None:
        raise ValueError

    # get the properties to return and the property map;
    # if we have a wildcard, get all the properties
    properties = [p.lower().strip() for p in input['properties']]
    if len(properties) == 1 and (properties[0] == '' or properties[0] == '*'):
        properties = list(get_item_info({}).keys())

    # get any configuration settings
    config = urllib.parse.parse_qs(input['config'])
    config = {k: v[0] for k, v in config.items()}
    limit = int(config.get('limit', 100))
    if limit >= 1000:
        limit = 1000
    headers = config.get('headers', 'true').lower()
    if headers == 'true':
        headers = True
    else:
        headers = False

    # write the output
    flex.output.content_type = 'application/json'
    flex.output.write('[')

    first_row = True
    if headers is True:
        result = json.dumps(properties)
        first_row = False
        flex.output.write(result)

    for item in get_data(params, limit):
        result = json.dumps([item.get(p) for p in properties])
        if first_row is False:
            result = ',' + result
        first_row = False
        flex.output.write(result)

    flex.output.write(']')

def get_data(params, limit):

    # see here for more info:
    # - https://hn.algolia.com/api
    # - https://www.algolia.com/doc/api-reference/api-parameters/

    url_query_params = {
        "query": params["filter"],
        "tags": "comment",
        "restrictSearchableAttributes": "comment_text",    # limit search to comments
        "disableTypoToleranceOnAttributes": "comment_text" # don't allow typos when searching for words
    }
    url = 'https://hn.algolia.com/api/v1/search'

    page_size = 100
    page_idx = 0
    row_idx = 0
    while True:

        url_query_params['hitsPerPage'] = page_size
        url_query_params['page'] = page_idx
        url_query_str = urllib.parse.urlencode(url_query_params)
        page_url = url + '?' + url_query_str

        response = requests_retry_session().get(page_url)
        content = response.json()
        data = content.get('hits',[])

        if len(data) == 0: # sanity check in case there's an issue with cursor
            break

        for item in data:
            if row_idx >= limit:
                break
            yield get_item_info(item)
            row_idx = row_idx + 1

        page_idx = content.get('page')
        page_count = content.get('nbPages')

        if page_idx is None:
            break
        if page_idx >= page_count-1:
            break
        if row_idx >= limit:
            break

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def validator_list(field, value, error):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                error(field, 'Must be a list with only string values')
        return
    error(field, 'Must be a string or a list of strings')

def to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal)):
        return str(value)
    return value

def to_list(value):
    # if we have a list of strings, create a list from them; if we have
    # a list of lists, flatten it into a single list of strings
    if isinstance(value, str):
        return value.split(",")
    if isinstance(value, list):
        return list(itertools.chain.from_iterable(value))
    return None

def get_item_info(item):

    # map this function's property names to the API's property names
    info = OrderedDict()

    info['title'] = item.get('title')
    info['url'] = item.get('url')
    info['author'] = item.get('author')
    info['comment'] = item.get('comment_text')
    info['parent_id'] = item.get('parent_id')
    info['created_at'] = item.get('created_at')

    return info
