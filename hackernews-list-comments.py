# ---
# name: hackernews-list-comments
# deployed: true
# title: Hacker News List Comments
# description: Returns the 100-most-recent Hacker News comments matching the search term
# params:
# - name: search
#   type: string
#   description: Search string to use to find the comments to return
#   required: true
# - name: properties
#   type: array
#   description: The properties to return (defaults to all properties). See "Notes" for a listing of the available properties.
#   required: false
# examples:
# - '"microsoft"'
# - '"google"'
# notes: |
#   The following properties are allowed:
#     * `title`: the title of the story
#     * `url`: the url of the story
#     * `author`: the user who made the comment
#     * `comment`: the comment text
#     * `parent_id`: the parent id
#     * `created_at`: the date the story was created
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
    property_map['title'] = 'story_title'
    property_map['url'] = 'story_url'
    property_map['author'] = 'author'
    property_map['comment'] = 'comment_text'
    property_map['parent_id'] = 'parent_id'
    property_map['created_at'] = 'created_at'

    try:

        # make the request
        # see here for more info:
        # - https://hn.algolia.com/api
        # - https://www.algolia.com/doc/api-reference/api-parameters/
        url_query_params = {
            "query": input["search"],
            "tags": "comment",
            "hitsPerPage": 100,
            "restrictSearchableAttributes": "comment_text",    # limit search to comments
            "disableTypoToleranceOnAttributes": "comment_text" # don't allow typos when searching for words
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

