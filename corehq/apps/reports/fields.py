from corehq.apps.domain.models import Domain, LICENSES
from corehq.apps.orgs.models import Organization
from corehq.apps.reports import util
from corehq.apps.reports.custom import ReportField, ReportSelectField
from corehq.apps.groups.models import Group
from corehq.apps.reports.models import HQUserType
from dimagi.utils.couch.database import get_db
from dimagi.utils.dates import DateSpan
from dimagi.utils.decorators.datespan import datespan_in_request
import settings

datespan_default = datespan_in_request(
            from_param="startdate",
            to_param="enddate",
            default_days=7,
        )

class GroupField(ReportSelectField):
    slug = "group"
    name = "Group"
    default_option = "Everybody"
    cssId = "group_select"

    def update_params(self):
        super(GroupField, self).update_params()
        self.groups = Group.get_reporting_groups(self.domain)
        self.options = [dict(val=group.get_id, text=group.name) for group in self.groups]

class CaseSharingGroupField(GroupField):
    default_option = "Any Group"
    cssClasses = "span6"

    def update_params(self):
        super(CaseSharingGroupField, self).update_params()
        self.options = [dict(val=group.get_id, text="%s [Case Sharing]"
                        % group.name if group.case_sharing else group.name)
                            for group in self.groups]

class FilterUsersField(ReportField):
    slug = "ufilter"
    template = "reports/fields/filter_users.html"

    def update_context(self):
        toggle, show_filter = self.get_user_filter(self.request)
        self.context['show_user_filter'] = show_filter
        self.context['toggle_users'] = toggle

    @classmethod
    def get_user_filter(cls, request):
        ufilter = group = individual = None
        try:
            if request.GET.get('ufilter', ''):
                ufilter = request.GET.getlist('ufilter')
            group = request.GET.get('group', '')
            individual = request.GET.get('individual', '')
        except KeyError:
            pass
        show_filter = True
        toggle = HQUserType.use_defaults()
        if ufilter and not (group or individual):
            toggle = HQUserType.use_filter(ufilter)
        elif group or individual:
            show_filter = False
        return toggle, show_filter

class CaseTypeField(ReportSelectField):
    slug = "case_type"
    name = "Case Type"
    cssId = "case_type_select"

    def update_params(self):
        individual = self.request.GET.get('individual', '')
        group = self.request.GET.get('group', '')
        if not individual and not settings.LUCENE_ENABLED:
            user_filter = HQUserType.use_filter(['0','1','2','3'])
        else:
            user_filter, _ = FilterUsersField.get_user_filter(self.request)

        users = util.get_all_users_by_domain(self.domain, group, individual, user_filter)
        user_ids = [user.user_id for user in users]
        
        case_types = self.get_case_types(self.domain, user_ids)
        case_type = self.request.GET.get(self.slug, '')

        open_count, all_count = self.get_case_counts(self.domain, user_ids=user_ids)
        self.selected = case_type
        self.options = [dict(val=case, text="%s (%d/%d open)" % (case, data.get("open", 0), data.get("all", 0)))
                        for case, data in case_types.items()]
        self.default_option = "All Case Types (%d/%d open)" % (open_count, all_count)

    @classmethod
    def get_case_types(cls, domain, user_ids=None):
        case_types = {}
        key = [domain]
        for r in get_db().view('hqcase/all_cases',
            startkey=key,
            endkey=key + [{}],
            group_level=2
        ).all():
            case_type = r['key'][1]
            if case_type:
                open_count, all_count = cls.get_case_counts(domain, case_type, user_ids)
                case_types[case_type] = {'open': open_count, 'all': all_count}
        return case_types

    @classmethod
    def get_case_counts(cls, domain, case_type=None, user_ids=None):
        """ Returns open count, all count
        """
        user_ids = user_ids or [{}]
        for view_name in ('hqcase/open_cases', 'hqcase/all_cases'):
            def individual_counts():
                for user_id in user_ids:
                    key = [domain, case_type or {}, user_id]
                    try:
                        yield get_db().view(view_name,
                            startkey=key,
                            endkey=key + [{}],
                            group_level=0
                        ).one()['value']
                    except TypeError:
                        yield 0
            yield sum(individual_counts())

class SelectFormField(ReportSelectField):
    slug = "form"
    name = "Form Type"
    cssId = "form_select"
    cssClasses = "span6"
    default_option = "Select a Form"

    def update_params(self):
        self.options = util.form_list(self.domain)
        self.selected = self.request.GET.get(self.slug, None)

class SelectAllFormField(SelectFormField):
    default_option = "All Forms"

class SelectOpenCloseField(ReportSelectField):
    slug = "is_open"
    name = "Opened / Closed"
    cssId = "opened_closed"
    cssClasses = "span3"
    default_option = "Show All"
    options = [dict(val="open", text="Only Open"),
               dict(val="closed", text="Only Closed")]

class SelectApplicationField(ReportSelectField):
    slug = "app"
    name = "Application"
    cssId = "application_select"
    cssClasses = "span6"
    default_option = "Select Application [Latest Build Version]"

    def update_params(self):
        apps_for_domain = get_db().view("app_manager/applications_brief",
            startkey=[self.domain],
            endkey=[self.domain, {}],
            include_docs=True).all()
        available_apps = [dict(val=app['value']['_id'],
                                text="%s [up to build %s]" % (app['value']['name'], app['value']['version']))
                          for app in apps_for_domain]
        self.selected = self.request.GET.get(self.slug,'')
        self.options = available_apps

class SelectOrganizationField(ReportSelectField):
    slug = "org"
    name = "Organization"
    cssId = "organization_select"
    cssClasses = "span6"
    default_option = "All Organizations"

    def update_params(self):
        available_orgs = [(o.title) for o in Organization.get_all()]
        available_orgs = [dict(val= name, text=name) for name in available_orgs]
        self.selected = self.request.GET.get(self.slug,'')
        self.options = available_orgs

class SelectCategoryField(ReportSelectField):
    slug = "category"
    name = "Category"
    cssId = "category_select"
    cssClasses = "span6"
    default_option = "All Categories"

    def update_params(self):
        available_categories = [(d.replace(' ', '+'), d) for d in Domain.categories()]
        available_categories = [dict(val=choice[1], text=choice[1]) for choice in available_categories]
        self.selected = self.request.GET.get(self.slug,'')
        self.options = available_categories

class SelectLicenseField(ReportSelectField):
    slug = "license"
    name = "License"
    cssId = "license_select"
    cssClasses = "span6"
    default_option = "All Licenses"

    def update_params(self):
        available_licenses = LICENSES.items()
        available_licenses = [dict(val=choice[1], text=choice[1]) for choice in available_licenses]
        self.selected = self.request.GET.get(self.slug,'')
        self.options = available_licenses

class SelectRegionField(ReportSelectField):
    slug = "region"
    name = "Region"
    cssId = "region_select"
    cssClasses = "span6"
    default_option = "All Regions"

    def update_params(self):
        available_regions = [(d.replace(' ', '+'), d) for d in Domain.regions()]
        available_regions = [dict(val=choice, text=choice) for choice in available_regions]
        self.selected = self.request.GET.get(self.slug,'')
        self.options = available_regions


class SelectMobileWorkerField(ReportField):
    slug = "select_mw"
    template = "reports/fields/select_mobile_worker.html"
    name = "Select Mobile Worker"
    default_option = "All Mobile Workers"

    def update_params(self):
        pass

    def update_context(self):
        self.user_filter, _ = FilterUsersField.get_user_filter(self.request)
        self.individual = self.request.GET.get('individual', '')
        self.default_option = self.get_default_text(self.user_filter)
        self.users = util.user_list(self.domain)

        self.update_params()

        self.context['field_name'] = self.name
        self.context['default_option'] = self.default_option
        self.context['users'] = self.users
        self.context['individual'] = self.individual

    @classmethod
    def get_default_text(cls, user_filter):
        default = cls.default_option
        if user_filter[HQUserType.ADMIN].show or \
           user_filter[HQUserType.DEMO_USER].show or user_filter[HQUserType.UNKNOWN].show:
            default = '%s & Others' % default
        return default

class SelectFilteredMobileWorkerField(SelectMobileWorkerField):
    """
        This is a little field for use when a client really wants to filter by individuals from a specific group.
        Since by default we still want to show all the data, no filtering is done unless the special group filter is selected.
    """
    slug = "select_filtered_mw"
    name = "Select Mobile Worker"
    default_option = "All Mobile Workers"
    template = "reports/fields/select_filtered_mobile_worker.html"
    default_option = "Showing All Mobile Workers..."

    group_names = []

    def update_params(self):
        if not self.individual:
            self.individual = self.request.GET.get('filtered_individual', '')
        self.users = []
        self.group_options = []
        for group in self.group_names:
            filtered_group = Group.by_name(self.domain, group)
            if filtered_group:
                self.group_options.append(dict(group_id=filtered_group._id,
                    name="Only %s Mobile Workers" % group))
                self.users.extend(filtered_group.get_users(is_active=True, only_commcare=True))

    def update_context(self):
        super(SelectFilteredMobileWorkerField, self).update_context()
        self.context['users'] = self.users_to_options(self.users)
        self.context['group_options'] = self.group_options

    @staticmethod
    def users_to_options(user_list):
        return [dict(val=user.user_id,
            text=user.raw_username,
            is_active=user.is_active) for user in user_list]


class DatespanField(ReportField):
    slug = "datespan"
    template = "reports/fields/datespan.html"

    def update_context(self):
        self.datespan = DateSpan.since(7, format="%Y-%m-%d", timezone=self.timezone)
        if self.request.datespan.is_valid():
            self.datespan.startdate = self.request.datespan.startdate
            self.datespan.enddate = self.request.datespan.enddate
        self.context['timezone'] = self.timezone.zone
        self.context['datespan'] = self.datespan

class DeviceLogTagField(ReportField):
    slug = "logtag"
    errors_only_slug = "errors_only"
    template = "reports/fields/devicelog_tags.html"

    def update_context(self):
        errors_only = bool(self.request.GET.get(self.errors_only_slug, False))
        self.context['errors_only_slug'] = self.errors_only_slug
        self.context[self.errors_only_slug] = errors_only

        selected_tags = self.request.GET.getlist(self.slug)
        show_all = bool(not selected_tags)
        self.context['default_on'] = show_all
        data = get_db().view('phonelog/device_log_tags', group=True)
        tags = [dict(name=item['key'],
                    show=bool(show_all or item['key'] in selected_tags))
                    for item in data]
        self.context['logtags'] = tags
        self.context['slug'] = self.slug

class DeviceLogFilterField(ReportField):
    slug = "logfilter"
    template = "reports/fields/devicelog_filter.html"
    view = "phonelog/devicelog_data"
    filter_desc = "Filter Logs By"

    def update_context(self):
        selected = self.request.GET.getlist(self.slug)
        show_all = bool(not selected)
        self.context['default_on'] = show_all

        data = get_db().view(self.view,
            startkey = [self.domain],
            endkey = [self.domain, {}],
            group=True)
        filters = [dict(name=item['key'][-1],
                    show=bool(show_all or item['key'][-1] in selected))
                        for item in data]
        self.context['filters'] = filters
        self.context['slug'] = self.slug
        self.context['filter_desc'] = self.filter_desc

class DeviceLogUsersField(DeviceLogFilterField):
    slug = "loguser"
    view = "phonelog/devicelog_data_users"
    filter_desc = "Filter Logs by Username"

class DeviceLogDevicesField(DeviceLogFilterField):
    slug = "logdevice"
    view = "phonelog/devicelog_data_devices"
    filter_desc = "Filter Logs by Device"


