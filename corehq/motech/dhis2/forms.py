from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from crispy_forms import bootstrap as twbscrispy
from crispy_forms import layout as crispy
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from corehq.apps.hqwebapp import crispy as hqcrispy
from corehq.apps.userreports.dbaccessors import get_report_configs_for_domain
from corehq.apps.userreports.ui.fields import JsonField
from corehq.motech.models import ConnectionSettings

from .const import SEND_FREQUENCY_CHOICES, SEND_FREQUENCY_MONTHLY
from .models import SQLDataSetMap


class DataSetMapForm(forms.ModelForm):
    description = forms.CharField(
        label=_('Description'),
    )
    frequency = forms.ChoiceField(
        label=_('Frequency'),
        choices=SEND_FREQUENCY_CHOICES,
        initial=SEND_FREQUENCY_MONTHLY,
    )
    day_to_send = forms.CharField(
        label=_('Day to send data'),
        help_text=_('Day of the month if "Frequency" is monthly or quarterly. '
                    'Day of the week if "Frequency" is weekly, where Monday '
                    'is 1 and Sunday is 7.'),
    )
    data_set_id = forms.CharField(
        label=_('DataSetID'),
        help_text=_('Set DataSetID if this UCR adds values to an existing '
                    'DHIS2 DataSet'),
        required=False,
    )
    org_unit_id = forms.CharField(
        label=_('OrgUnitID'),
        required=False,
    )
    org_unit_column = forms.CharField(
        label=_('OrgUnitID column'),
        help_text=_('Please set either a fixed value for "OrgUnitID", or '
                    'specify an "OrgUnitID column" where a DHIS2 Organisation '
                    'Unit ID will be found.'),
        required=False,
    )
    period = forms.CharField(
        label=_('Period'),
        required=False,
    )
    period_column = forms.CharField(
        label=_('Period column'),
        help_text=_('Please set a fixed value for "Period", or specify a '
                    '"Period column" where a period will be found, or if the '
                    'UCR has a date filter then leave both fields blank to '
                    'filter the UCR by the date range of the previous '
                    'period.'),
        required=False,
    )
    attribute_option_combo_id = forms.CharField(
        label=_('AttributeOptionComboID'),
        required=False,
    )
    complete_date = forms.DateField(
        label=_('CompleteDate'),
        required=False,
    )

    class Meta:
        model = SQLDataSetMap
        fields = [
            'description',
            'connection_settings',
            'ucr_id',
            'frequency',
            'day_to_send',
            'data_set_id',
            'org_unit_id',
            'org_unit_column',
            'period',
            'period_column',
            'attribute_option_combo_id',
            'complete_date',
        ]

    def __init__(self, domain, *args, **kwargs):
        from corehq.motech.dhis2.views import DataSetMapListView

        super().__init__(*args, **kwargs)
        self.domain = domain
        self.fields['connection_settings'] = get_connection_settings_field(domain)
        self.fields['ucr_id'] = get_ucr_field(domain)

        self.helper = hqcrispy.HQFormHelper()
        self.helper.layout = crispy.Layout(
            crispy.Fieldset(
                _('DataSet Details'),
                crispy.Field('description'),
                crispy.Field('connection_settings'),
                crispy.Field('ucr_id'),
                crispy.Field('frequency'),
                crispy.Field('day_to_send'),
                crispy.Field('data_set_id'),
                crispy.Field('org_unit_id'),
                crispy.Field('org_unit_column'),
                crispy.Field('period'),
                crispy.Field('period_column'),
                crispy.Field('attribute_option_combo_id'),
                crispy.Field('complete_date'),
            ),
            hqcrispy.FormActions(
                twbscrispy.StrictButton(
                    _("Save"),
                    type="submit",
                    css_class="btn btn-primary",
                ),
                hqcrispy.LinkButton(
                    _("Cancel"),
                    reverse(
                        DataSetMapListView.urlname,
                        kwargs={'domain': self.domain},
                    ),
                    css_class="btn btn-default",
                ),
            ),
        )

    def save(self, commit=True):
        self.instance.domain = self.domain
        return super().save(commit)

    def clean(self):
        cleaned_data = super().clean()

        if not (
            cleaned_data.get('org_unit_id')
            or cleaned_data.get('org_unit_column')
        ):
            self.add_error('org_unit_column', _(
                'Please set either a fixed value for "OrgUnitID", or '
                'specify an "OrgUnitID column" where a DHIS2 Organisation '
                'Unit ID will be found.'
            ))

        if (
            cleaned_data.get('org_unit_id')
            and cleaned_data.get('org_unit_column')
        ):
            self.add_error('org_unit_column', _(
                'Please set either a fixed value for "OrgUnitID", or '
                'specify an "OrgUnitID column" where a DHIS2 Organisation '
                'Unit ID will be found, but not both.'
            ))

        if (
            cleaned_data.get('period')
            and cleaned_data.get('period_column')
        ):
            self.add_error('period_column', _(
                'Please set a fixed value for "Period", or specify a "Period '
                'column" where a period will be found, or if the UCR has a '
                'date filter then leave both fields blank to filter the UCR '
                'by the date range of the previous period. Do not set both '
                '"Period" and "Period column".'
            ))

        return self.cleaned_data


def get_connection_settings_field(domain):
    from corehq.motech.views import ConnectionSettingsListView

    connection_settings = ConnectionSettings.objects.filter(domain=domain)
    url = reverse(ConnectionSettingsListView.urlname,
                  kwargs={'domain': domain})
    return forms.ModelChoiceField(
        label=_("Connection Settings"),
        queryset=connection_settings,
        required=True,
        help_text=_(f'<a href="{url}">Add/Edit Connections Settings</a>')
    )


def get_ucr_field(domain):
    from corehq.apps.userreports.views import UserConfigReportsHomeView

    ucrs = get_report_configs_for_domain(domain)
    url = reverse(UserConfigReportsHomeView.urlname,
                  kwargs={'domain': domain})
    return forms.ChoiceField(
        label=_("User Configurable Report"),
        choices=[(ucr.get_id, ucr.title) for ucr in ucrs],
        required=True,
        help_text=_(
            'DataSet Maps map CommCare UCRs to DHIS2 DataSets. '
            '<a href="https://github.com/dimagi/commcare-hq/blob/master/corehq/motech/dhis2/README.md#datasets" '
            f'target="_new">More info</a>. '
            f'Go to <a href="{url}">Configurable Reports</a> to define a UCR.')
    )


class Dhis2ConfigForm(forms.Form):
    form_configs = JsonField(expected_type=list)

    def __init__(self, *args, **kwargs):
        super(Dhis2ConfigForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _('Save Changes')))

    def clean_form_configs(self):
        errors = _validate_form_configs(self.cleaned_data['form_configs'])
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data['form_configs']


class Dhis2EntityConfigForm(forms.Form):
    """
    Dhis2EntityConfig.case_configs is a list. Dhis2EntityConfigForm has
    one case_config, and is used in a formset.
    """
    case_config = JsonField()

    def clean_case_config(self):
        errors = []
        case_config = self.cleaned_data['case_config']
        if not isinstance(case_config, dict):
            raise ValidationError(
                _('The "case_type" property is a dictionary, not a "%(data_type)s".'),
                params={'data_type': type(case_config).__name__}
            )
        if not case_config.get('case_type'):
            errors.append(ValidationError(
                _('The "%(property)s" property is required.'),
                params={'property': 'case_type'},
                code='required_property',
            ))
        if 'form_configs' not in case_config:
            errors.append(ValidationError(
                _('The "%(property)s" property is required.'),
                params={'property': 'form_configs'},
                code='required_property',
            ))
        elif not isinstance(case_config['form_configs'], list):
            raise ValidationError(
                _('The "form_configs" property is a dictionary, not a "%(data_type)s".'),
                params={'data_type': type(case_config['form_configs']).__name__}
            )
        else:
            errors.extend(_validate_form_configs(case_config['form_configs']))
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data['case_config']


def _validate_form_configs(form_configs):
    errors = []
    for form_config in form_configs:
        if form_config.get('xmlns'):
            required_msg = _('The "%(property)s" property is required for '
                             'form "{}".').format(form_config['xmlns'])
        else:
            required_msg = _('The "%(property)s" property is required.')

        if not form_config.get('xmlns'):
            errors.append(ValidationError(
                '{} {}'.format(required_msg, _('Please specify the XMLNS of the form.')),
                params={'property': 'xmlns'},
                code='required_property',
            ))
        if not form_config.get('program_id'):
            errors.append(ValidationError(
                '{} {}'.format(required_msg, _('Please specify the DHIS2 Program of the event.')),
                params={'property': 'program_id'},
                code='required_property',
            ))
        if not form_config.get('datavalue_maps'):
            errors.append(ValidationError(
                '{} {}'.format(required_msg, _('Please map CommCare values to DHIS2 data elements.')),
                params={'property': 'datavalue_maps'},
                code='required_property',
            ))
    return errors
