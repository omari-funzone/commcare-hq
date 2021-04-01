from collections import defaultdict
from functools import partial
from operator import attrgetter
from xml.etree import cElementTree as ElementTree

from casexml.apps.phone.fixtures import FixtureProvider
from casexml.apps.phone.utils import (
    GLOBAL_USER_ID,
    get_or_cache_global_fixture,
)
from corehq.apps.fixtures.dbaccessors import iter_fixture_items_for_data_type
from corehq.apps.fixtures.models import FIXTURE_BUCKET, FixtureDataType
from corehq.apps.products.fixtures import product_fixture_generator_json
from corehq.apps.programs.fixtures import program_fixture_generator_json
from corehq.util.metrics import metrics_histogram
from .utils import get_index_schema_node


def item_lists_by_domain(domain):
    ret = list()
    for data_type in FixtureDataType.by_domain(domain):
        structure = {
            f.field_name: {
                'name': f.field_name,
                'no_option': True
            } for f in data_type.fields
        }

        for attr in data_type.item_attributes:
            structure['@' + attr] = {'name': attr, 'no_option': True}

        uri = 'jr://fixture/%s:%s' % (ItemListsProvider.id, data_type.tag)
        ret.append({
            'id': data_type.tag,
            'uri': uri,
            'path': "/{tag}_list/{tag}".format(tag=data_type.tag),
            'name': data_type.tag,
            'structure': structure,
        })
    ret = sorted(ret, key=lambda x: x['name'].lower())

    products = product_fixture_generator_json(domain)
    if products:
        ret.append(products)
    programs = program_fixture_generator_json(domain)
    if programs:
        ret.append(programs)
    return ret


def item_lists_by_app(app):
    LOOKUP_TABLE_FIXTURE = 'lookup_table_fixture'
    REPORT_FIXTURE = 'report_fixture'
    lookup_lists = item_lists_by_domain(app.domain).copy()
    for item in lookup_lists:
        item['fixture_type'] = LOOKUP_TABLE_FIXTURE

    report_configs = [
        report_config
        for module in app.get_report_modules()
        for report_config in module.report_configs
    ]
    ret = list()
    for config in report_configs:
        uri = 'jr://fixture/commcare-reports:%s' % (config.uuid)
        ret.append({
            'id': config.uuid,
            'uri': uri,
            'path': "/rows/row",
            'name': config.header.get('en'),
            'structure': {},
            'fixture_type': REPORT_FIXTURE,
        })
    return lookup_lists + ret


class ItemListsProvider(FixtureProvider):
    id = 'item-list'

    def __call__(self, restore_state):
        restore_user = restore_state.restore_user
        global_types = {}
        user_types = {}
        for data_type in FixtureDataType.by_domain(restore_user.domain):
            if data_type.is_global:
                global_types[data_type._id] = data_type
            else:
                user_types[data_type._id] = data_type
        items = global_items = user_items = []
        if global_types:
            global_items = self.get_global_items(global_types, restore_state)
            items.extend(global_items)
        if user_types:
            user_items = self.get_user_items(user_types, restore_user)
            items.extend(user_items)

        for metric_name, items_count in [
            ('commcare.fixtures.item_lists.global', len(global_items)),
            ('commcare.fixtures.item_lists.user', len(user_items)),
            ('commcare.fixtures.item_lists.all', len(items)),
        ]:
            metrics_histogram(
                metric_name,
                items_count,
                bucket_tag='items',
                buckets=[1, 100, 1000, 10000, 30000, 100000, 300000, 1000000],
                bucket_unit='',
                tags={
                    'domain': restore_user.domain
                }
            )
        return items

    def get_global_items(self, global_types, restore_state):
        domain = restore_state.restore_user.domain
        data_fn = partial(self._get_global_items, global_types, domain)
        return get_or_cache_global_fixture(restore_state, FIXTURE_BUCKET, '', data_fn)

    def _get_global_items(self, global_types, domain):
        def get_items_by_type(data_type):
            for item in iter_fixture_items_for_data_type(domain, data_type._id):
                self._set_cached_type(item, data_type)
                yield item

        return self._get_fixtures(global_types, get_items_by_type, GLOBAL_USER_ID)

    def get_user_items(self, user_types, restore_user):
        items_by_type = defaultdict(list)
        for item in restore_user.get_fixture_data_items():
            data_type = user_types.get(item.data_type_id)
            if data_type:
                self._set_cached_type(item, data_type)
                items_by_type[data_type].append(item)

        def get_items_by_type(data_type):
            return sorted(items_by_type.get(data_type, []),
                          key=attrgetter('sort_key'))

        return self._get_fixtures(user_types, get_items_by_type, restore_user.user_id)

    def _set_cached_type(self, item, data_type):
        # set the cached version used by the object so that it doesn't
        # have to do another db trip later
        item._data_type = data_type

    def _get_fixtures(self, data_types, get_items_by_type, user_id):
        fixtures = []
        for data_type in sorted(data_types.values(), key=attrgetter('tag')):
            if data_type.is_indexed:
                fixtures.append(self._get_schema_element(data_type))
            items = get_items_by_type(data_type)
            fixtures.append(self._get_fixture_element(data_type, user_id, items))
        return fixtures

    def _get_fixture_element(self, data_type, user_id, items):
        attrib = {
            'id': ':'.join((self.id, data_type.tag)),
            'user_id': user_id
        }
        if data_type.is_indexed:
            attrib['indexed'] = 'true'
        fixture_element = ElementTree.Element('fixture', attrib)
        item_list_element = ElementTree.Element('%s_list' % data_type.tag)
        fixture_element.append(item_list_element)
        for item in items:
            item_list_element.append(item.to_xml())
        return fixture_element

    def _get_schema_element(self, data_type):
        attrs_to_index = [field.field_name for field in data_type.fields if field.is_indexed]
        fixture_id = ':'.join((self.id, data_type.tag))
        return get_index_schema_node(fixture_id, attrs_to_index)


item_lists = ItemListsProvider()
