import logging
from django.urls import reverse
from django.http import Http404
import json
from django.utils.html import format_html
from corehq.apps.api.es import ReportFormESView
from corehq.apps.hqwebapp.decorators import use_timeago
from corehq.apps.reports.datatables import DataTablesColumn, DataTablesHeader
from corehq.apps.reports.view_helpers import case_hierarchy_context
from pact.enums import PACT_DOMAIN
from pact.forms.patient_form import PactPatientForm
from pact.forms.weekly_schedule_form import ScheduleForm
from pact.models import PactPatientCase
from pact.reports import PactDrilldownReportMixin, PactElasticTabularReportMixin
from pact.utils import pact_script_fields, get_by_case_id_form_es_query


class PactPatientInfoReport(PactDrilldownReportMixin, PactElasticTabularReportMixin):
    slug = "patient"
    description = "some patient"

    hide_filters = True
    filters = []
    ajax_pagination = True
    xform_es = ReportFormESView(PACT_DOMAIN)

    default_sort = {
        "received_on": "desc"
    }

    name = "Patient Info"

    @use_timeago
    def decorator_dispatcher(self, request, *args, **kwargs):
        return super(PactPatientInfoReport, self).decorator_dispatcher(request, *args, **kwargs)

    @property
    def patient_id(self):
        return self.request.GET.get('patient_id')

    def get_case(self):
        if self.patient_id is None:
            return None
        return PactPatientCase.get(self.patient_id)

    @property
    def report_context(self):
        from pact import api
        ret = {}
        try:
            patient_doc = self.get_case()
            has_error = False
        except Exception as ex:
            logging.exception('problem getting pact patient data for patient {}. {}'.format(
                self.patient_id, ex
            ))
            has_error = True
            patient_doc = None

        if patient_doc is None:
            self.report_template_path = "pact/patient/nopatient.html"
            if has_error:
                ret['error_message'] = "Patient not found"
            else:
                ret['error_message'] = "No patient selected"
            return ret

        view_mode = self.request.GET.get('view', 'info')
        ret['patient_doc'] = patient_doc
        ret['pt_root_url'] = patient_doc.get_info_url()
        ret['view_mode'] = view_mode

        if view_mode == 'info':
            self.report_template_path = "pact/patient/pactpatient_info.html"
            ret['cloudcare_addr_edit_url'] = api.get_cloudcare_url(patient_doc._id,
                                                                   api.FORM_ADDRESS)
            ret['cloudcare_pn_url'] = api.get_cloudcare_url(patient_doc._id, api.FORM_PROGRESS_NOTE)
            ret['cloudcare_dot_url'] = api.get_cloudcare_url(patient_doc._id, api.FORM_DOT)
            ret['cloudcare_bw_url'] = api.get_cloudcare_url(patient_doc._id, api.FORM_BLOODWORK)
        elif view_mode == 'submissions':
            tabular_context = super(PactPatientInfoReport, self).report_context
            tabular_context.update(ret)
            self.report_template_path = "pact/patient/pactpatient_submissions.html"
            return tabular_context
        elif view_mode == 'schedule':
            the_form = ScheduleForm()
            ret['schedule_form'] = the_form
            ret['schedule_fields'] = json.dumps(list(the_form.fields.keys()))
            self.report_template_path = "pact/patient/pactpatient_schedule.html"
        elif view_mode == 'edit':
            the_form = PactPatientForm(self.request, patient_doc)
            ret['patient_form'] = the_form
            self.report_template_path = "pact/patient/pactpatient_edit.html"
        elif view_mode == 'providers':
            self.report_template_path = "pact/patient/pactpatient_providers.html"
        elif view_mode == 'careplan':
            ret.update(case_hierarchy_context(patient_doc,
                lambda case_id: reverse('case_data', args=[PACT_DOMAIN, case_id]),
                show_view_buttons=False
            ))
            self.report_template_path = "pact/patient/pactpatient_careplan.html"
        else:
            raise Http404
        return ret

    @property
    def headers(self):
        return DataTablesHeader(
            DataTablesColumn("Show Form", sortable=False, span=1),
            DataTablesColumn("Received", prop_name="received_on", span=1),
            DataTablesColumn("Created Date", prop_name="form.meta.timeStart", span=1),
            DataTablesColumn("Encounter Date", sortable=False, span=1),
            DataTablesColumn("Form", prop_name="form.#type", span=1),
            DataTablesColumn("CHW", prop_name="form.meta.username", span=1)
        )

    @property
    def es_results(self):
        if not self.patient_id:
            return None

        fields = [
            "_id",
            "received_on",
            "form.meta.timeEnd",
            "form.meta.timeStart",
            "form.meta.username",
            "form.#type",
        ]
        full_query = (get_by_case_id_form_es_query(self.pagination.start, self.pagination.count, self.patient_id)
            .source(fields).raw_query)
        full_query.update({
            "sort": self.get_sorting_block(),
            "script_fields": pact_script_fields()
        })
        res = self.xform_es.run_query(full_query)
        return res

    @property
    def rows(self):
        if self.patient_id:
            def _format_row(row_field_dict):
                yield format_html(
                    "<a class='ajax_dialog' href='{}'>View</a>",
                    reverse('render_form_data', args=[self.domain, row_field_dict['_id']])
                )
                yield self.format_date(row_field_dict["received_on"].replace('_', ' '))
                yield self.format_date(row_field_dict.get("form.meta.timeStart", ""))
                if row_field_dict["script_encounter_date"] is not None:
                    yield row_field_dict["script_encounter_date"]
                else:
                    yield "---"
                yield row_field_dict["form.#type"].replace('_', ' ').title()
                yield row_field_dict.get("form.meta.username", "")

            res = self.es_results
            if 'error' in res:
                pass
            else:
                for result in res['hits']['hits']:
                    yield list(_format_row(result))
