from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.receiverwrapper.util import submit_form_locally
from corehq.form_processor.backends.sql.dbaccessors import FormAccessorSQL
from corehq.form_processor.utils.xform import (
    FormSubmissionBuilder,
    TestFormMetadata,
)
from corehq.motech.models import ConnectionSettings

from ..const import (
    RECORD_CANCELLED_STATE,
    RECORD_FAILURE_STATE,
    RECORD_PENDING_STATE,
)
from ..models import FormRepeater, RepeaterStub
from ..tasks import process_repeater_stub

DOMAIN = 'gaidhlig'
PAYLOAD_IDS = ['aon', 'dha', 'trì', 'ceithir', 'coig', 'sia', 'seachd', 'ochd',
               'naoi', 'deich']


class TestProcessRepeaterStub(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.domain = create_domain(DOMAIN)
        cls.connection_settings = ConnectionSettings.objects.create(
            domain=DOMAIN,
            name='Test API',
            url="http://localhost/api/"
        )

    def setUp(self):
        self.repeater = FormRepeater(
            domain=DOMAIN,
            connection_settings_id=self.connection_settings.id,
        )
        self.repeater.save()
        self.repeater_stub = RepeaterStub.objects.get(
            domain=DOMAIN,
            repeater_id=self.repeater.get_id,
        )
        just_now = timezone.now() - timedelta(seconds=10)
        for payload_id in PAYLOAD_IDS:
            self.repeater_stub.repeat_records.create(
                domain=self.repeater_stub.domain,
                payload_id=payload_id,
                registered_at=just_now,
            )
            just_now += timedelta(seconds=1)

    def tearDown(self):
        self.repeater.delete()

    @classmethod
    def tearDownClass(cls):
        cls.connection_settings.delete()
        cls.domain.delete()
        super().tearDownClass()

    def test_get_payload_fails(self):
        # If the payload of a repeat record is missing, it should be
        # cancelled, and process_repeater() should continue to the next
        # payload
        with patch('corehq.motech.repeaters.models.log_repeater_error_in_datadog'), \
                patch('corehq.motech.repeaters.tasks.metrics_counter'):
            process_repeater_stub(self.repeater_stub)

        # All records were tried and cancelled
        records = list(self.repeater_stub.repeat_records.all())
        self.assertEqual(len(records), 10)
        self.assertTrue(all(r.state == RECORD_CANCELLED_STATE for r in records))
        # All records have a cancelled Attempt
        self.assertTrue(all(len(r.attempts) == 1 for r in records))
        self.assertTrue(all(r.attempts[0].state == RECORD_CANCELLED_STATE
                            for r in records))

    def test_send_request_fails(self):
        # If send_request() should be retried with the same repeat
        # record, process_repeater() should exit
        with patch('corehq.motech.repeaters.models.simple_post') as post_mock, \
                patch('corehq.motech.repeaters.tasks.metrics_counter'), \
                form_context(PAYLOAD_IDS):
            post_mock.return_value = Mock(status_code=400, reason='Bad request')
            process_repeater_stub(self.repeater_stub)

        # Only the first record was attempted, the rest are still pending
        states = [r.state for r in self.repeater_stub.repeat_records.all()]
        self.assertListEqual(states, ([RECORD_FAILURE_STATE]
                                      + [RECORD_PENDING_STATE] * 9))


@contextmanager
def form_context(form_ids):
    for form_id in form_ids:
        builder = FormSubmissionBuilder(
            form_id=form_id,
            metadata=TestFormMetadata(domain=DOMAIN),
        )
        submit_form_locally(builder.as_xml_string(), DOMAIN)
    try:
        yield
    finally:
        FormAccessorSQL.hard_delete_forms(DOMAIN, form_ids)
