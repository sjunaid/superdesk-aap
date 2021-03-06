# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
from abc import ABCMeta, abstractmethod
from flask import render_template
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service
from bson import ObjectId
from superdesk.utc import utc_to_local, utcnow
from superdesk.metadata.item import PUBLISH_STATES, ITEM_STATE, ITEM_TYPE, CONTENT_TYPE, CONTENT_STATE
from eve.utils import config, ParsedRequest
from apps.desks import DeskTypes


class GenerateBodyHtml(metaclass=ABCMeta):

    def get_articles(self, query, repo):
        """Get the articles using search endpoint
        :param dict query:
        :param list repo:
        :return:
        """
        result = []
        processed = set()
        request = ParsedRequest()
        request.args = {'source': json.dumps(query), 'repo': ','.join(repo), 'aggregations': 0}
        items = list(get_resource_service('search').get(req=request, lookup=None))

        for item in items:
            if item.get(config.ID_FIELD) not in processed:
                processed.add(item.get(config.ID_FIELD))
                result.append(item)

        return result

    @abstractmethod
    def create_query(self):
        raise NotImplementedError()

    @abstractmethod
    def process(self):
        raise NotImplementedError()

    def generate(self, template_name, **kwargs):
        query, repo = self.create_query()
        articles = self.get_articles(query, repo)
        if not articles:
            return {}

        self.process(articles)
        kwargs['items'] = articles
        return render_template(template_name, **kwargs)


class GenerateBodyHtmlForPublishedArticlesByDesk(GenerateBodyHtml):

    def __init__(self, desk_id):
        self.desk_id = desk_id

    def create_query(self):
        if isinstance(self.desk_id, str):
            self.desk_id = ObjectId(self.desk_id)

        desk = get_resource_service('desks').find_one(req=None, _id=self.desk_id)

        if not desk:
            return {}, ''

        states = list(PUBLISH_STATES)
        states.extend([CONTENT_STATE.SUBMITTED, CONTENT_STATE.PROGRESS])
        # using the server default timezone.
        current_local_time = utc_to_local(config.DEFAULT_TIMEZONE, utcnow())

        query = {
            'query': {
                'filtered': {
                    'filter': {
                        'bool': {
                            'must': [
                                {
                                    'term': {ITEM_TYPE: CONTENT_TYPE.TEXT}
                                }
                            ],
                            'must_not': [
                                {
                                    'range': {
                                        'versioncreated': {
                                            "lte": current_local_time.strftime('%Y-%m-%dT00:00:00%z')
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            },
            'sort': [
                {'versioncreated': 'desc'}
            ],
            'size': 200
        }

        desk_query = query['query']['filtered']['filter']['bool']['must']
        if desk.get('desk_type') == DeskTypes.authoring.value:
            desk_filter = {'or': []}

            # if published from authoring desk
            desk_filter['or'].append({'and': [
                {'term': {'task.desk': str(self.desk_id)}},
                {'terms': {ITEM_STATE: list(PUBLISH_STATES)}}
            ]})

            # if published send from authoring desk
            desk_filter['or'].append({'and': [
                {'term': {'task.last_authoring_desk': str(self.desk_id)}},
                {'terms': {ITEM_STATE: states}}
            ]})

            desk_query.append(desk_filter)
        else:
            # filtering only published states for production for now.
            desk_query.append({'term': {'task.desk': str(self.desk_id)}})
            desk_query.append({'terms': {ITEM_STATE: list(PUBLISH_STATES)}})

        return query, ['archive', 'published']

    def process(self, articles):
        for article in articles:
            article['anpa_take_key'] = article.get('anpa_take_key') or ''
            article['abstract'] = article.get('abstract') or ''
            article['slugline'] = article.get('slugline') or ''
            article['source'] = article.get('source') or ''
            article['dateline_city'] = \
                (((article.get('dateline') or {}).get('located') or {}).get('city') or '').upper()


def generate_published_slugline_story_by_desk(item, **kwargs):
    """Marco function to generate slugline story by desk
    :param dict item: item on a desk
    :param kwargs:
    :return dict: modified item
    """
    if not item:
        raise SuperdeskApiError.badRequestError("Invalid article.")

    desk_id = item.get('task', {}).get('desk')

    if not desk_id:
        raise SuperdeskApiError.badRequestError("Article should be on a desk to run the macro.")

    desk_name = get_resource_service('desks').get_desk_name(desk_id)
    now = utcnow()
    fields = json.loads(GenerateBodyHtmlForPublishedArticlesByDesk(desk_id).generate('skeds_body_html.json',
                                                                                     desk_name=desk_name,
                                                                                     now=now))
    for key, value in fields.items():
        item[key] = value

    return item


name = 'skeds_by_desk'
label = 'Skeds By Desk'
callback = generate_published_slugline_story_by_desk
access_type = 'frontend'
action_type = 'direct'
order = 5
