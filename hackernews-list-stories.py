# ---
# name: hackernews-list-stories
# deployed: true
# title: Hacker News List Stories
# description: Returns a list of the top-100 Hacker News most-recent stories matching the search term
# params:
# - name: search
#   type: string
#   description: Search string to use to find the stories to return
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
#     * `user_id`: the user id of the user associated with the event
#     * `title`: the title of the story
#     * `url`: the url of the story
#     * `author`: the user who submitted the story
#     * `points`: the number of points the story has
#     * `story_text`: the story text
#     * `comment_text`: the comment text
#     * `num_comments`: the number of comments
#     * `story_id`: the story id
#     * `story_title`: the story title
#     * `story_url`: the story url
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
    property_map['title'] = 'title'
    property_map['url'] = 'url'
    property_map['author'] = 'author'
    property_map['points'] = 'points'
    property_map['story_text'] = 'story_text'
    property_map['comment_text'] = 'comment_text'
    property_map['num_comments'] = 'num_comments'
    property_map['story_id'] = 'story_id'
    property_map['story_title'] = 'story_title'
    property_map['story_url'] = 'story_url'
    property_map['parent_id'] = 'parent_id'
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

