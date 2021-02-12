from datetime import datetime
from django.test import SimpleTestCase, TestCase

from ..login_record import LoginRecord, EPOCH


class TestLoginRecord_Constructor(SimpleTestCase):
    def test_creates_valid_object(self):
        current_time = datetime(2020, 12, 5)
        record = LoginRecord('test_user', failures=4, last_attempt_date=current_time)
        self.assertEqual(record.username, 'test_user')
        self.assertEqual(record.failures, 4)
        self.assertEqual(record.last_attempt_date, current_time)

    def test_handles_default_arguments(self):
        record = LoginRecord('test_user')
        self.assertEqual(record.failures, 0)
        self.assertEqual(record.last_attempt_date, EPOCH)


class TestLoginRecord(TestCase):
    def setUp(self):
        # ensure 'test_user' doesn't exist already
        record = LoginRecord('test_user')
        record.clear()

    def tearDown(self):
        record = LoginRecord('test_user')
        record.clear()

    def test_get_populates_empty_user(self):
        record = LoginRecord.get('test_user')
        self.assertEqual(record.failures, 0)
        self.assertEqual(record.last_attempt_date, EPOCH)

    def test_clear_handles_missing_user(self):
        record = LoginRecord('missing_user')
        record.clear()

        self.assertEqual(record.failures, 0)
        self.assertEqual(record.last_attempt_date, EPOCH)

    def test_inserts_add_failure_increments_failure_count(self):
        record = LoginRecord.get('test_user')
        current_time = datetime(2020, 12, 5)
        record.add_failure(current_time)

        # ensure the record fields were updated after insert
        self.assertEqual(record.failures, 1)
        self.assertEqual(record.last_attempt_date, current_time)

        # ensure the database roundtrip
        inserted_record = LoginRecord.get('test_user')
        self.assertEqual(inserted_record.failures, 1)
        self.assertEqual(inserted_record.last_attempt_date, current_time)

    def test_clear_resets_user(self):
        record = LoginRecord.get('test_user')
        record.add_failure(datetime.utcnow())

        record.clear()

        # ensure the record fields were updated after clear
        self.assertEqual(record.failures, 0)
        self.assertEqual(record.last_attempt_date, EPOCH)

        cleared_record = LoginRecord.get('test_user')
        self.assertEqual(cleared_record.failures, 0)
        self.assertEqual(cleared_record.last_attempt_date, EPOCH)

    def test_multiple_failures_increment_failure_counter(self):
        record = LoginRecord.get('test_user')
        record.add_failure(datetime.utcnow())
        record.add_failure(datetime.utcnow())
        record.add_failure(datetime.utcnow())
        self.assertEqual(record.failures, 3)

    def test_interleaved_inserts_update_correctly(self):
        record_one = LoginRecord.get('test_user')
        record_two = LoginRecord.get('test_user')

        record_one.add_failure(datetime.utcnow())
        record_one.add_failure(datetime.utcnow())
        record_one.add_failure(datetime.utcnow())

        record_two.add_failure(datetime.utcnow())
        self.assertEqual(record_two.failures, 4)

    def test_failure_count_resets_on_new_day(self):
        record = LoginRecord('test_user')
        YESTERDAY_11_PM = datetime(2020, 12, 5, 23)
        TODAY_1_AM = datetime(2020, 12, 6, 1)

        record.add_failure(YESTERDAY_11_PM)
        record.add_failure(TODAY_1_AM)

        self.assertEqual(record.failures, 1)
        self.assertEqual(record.last_attempt_date, TODAY_1_AM)
