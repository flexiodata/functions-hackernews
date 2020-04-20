# ---
# name: hackernews-stories
# deployed: true
# title: Hacker News Stories
# description: Returns the 100-most-recent Hacker News stories matching the search term
# params:
#   - name: search
#     type: string
#     description: Search string to use to find the stories to return
#     required: true
#   - name: properties
#     type: array
#     description: The properties to return (defaults to all properties). See "Returns" for a listing of the available properties.
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
#     description: The user who submitted the story
#   - name: points
#     type: string
#     description: The number of points the story has
#   - name: num_comments
#     type: string
#     description: The number of comments
#   - name: created_at
#     type: string
#     description: The date the story was created
# examples:
#   - '"microsoft"'
#   - '"google"'
# ---

import json
import requests
import urllib
import itertools
from datetime import *
from decimal import *
from cerberus import Validator
from collections import OrderedDict

def flexio_handler(flex):

    # get the input
    input = flex.input.read()
    try:
        input = json.loads(input)
        if not isinstance(input, list): raise ValueError
    except ValueError:
        raise ValueError

    # define the expected parameters and map the values to the parameter names
    # based on the positions of the keys/values
    params = OrderedDict()
    params['search'] = {'required': True, 'type': 'string'}
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': '*'}
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    v = Validator(params, allow_unknown = True)
    input = v.validated(input)
    if input is None:
        raise ValueError

    # map this function's property names to the API's property names
    property_map = OrderedDict()
    property_map['title'] = 'title'
    property_map['url'] = 'url'
    property_map['author'] = 'author'
    property_map['points'] = 'points'
    property_map['num_comments'] = 'num_comments'
    property_map['created_at'] = 'created_at'

    try:

        # make the request
        # see here for more info:
        # - https://hn.algolia.com/api
        # - https://www.algolia.com/doc/api-reference/api-parameters/
        url_query_params = {
            "query": input["search"],
            "tags": "story",
            "hitsPerPage": 100,
            "restrictSearchableAttributes": "title",    # limit search to title
            "disableTypoToleranceOnAttributes": "title" # don't allow typos when searching for words
        }
        url_query_str = urllib.parse.urlencode(url_query_params)

        url = 'https://hn.algolia.com/api/v1/search_by_date?' + url_query_str
        response = requests.get(url)
        content = response.json()

        # get the properties to return and the property map
        properties = [p.lower().strip() for p in input['properties']]

        # if we have a wildcard, get all the properties
        if len(properties) == 1 and properties[0] == '*':
            properties = list(property_map.keys())

        # build up the result
        result = []

        result.append(properties)
        stories = content.get('hits',[])
        for item in stories:
            row = [item.get(property_map.get(p,''),'') or '' for p in properties]
            result.append(row)

        result = json.dumps(result, default=to_string)
        flex.output.content_type = "application/json"
        flex.output.write(result)

    except:
        raise RuntimeError

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
