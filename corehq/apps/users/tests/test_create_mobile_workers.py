from django.test import TestCase

from corehq.apps.domain.shortcuts import create_domain
from corehq.apps.users.models import CommCareUser


class TestCreateMobileWorkers(TestCase):
    domain = 'test_create_mobile_workers'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = create_domain(cls.domain)

    @classmethod
    def tearDownClass(cls):
        cls.project.delete()
        super().tearDownClass()

    def test_create_basic(self):
        user = CommCareUser.create(
            self.domain,
            'mw1',
            's3cr4t',
            email='mw1@example.com',
            device_id='my-pixel',
            first_name='Mobile',
            last_name='Worker',
        )
        self.addCleanup(user.delete)
        self.assertEqual(self.domain, user.domain)
        self.assertEqual('mw1', user.username)
        self.assertEqual('mw1@example.com', user.email)
        self.assertEqual(['my-pixel'], user.device_ids)
        self.assertEqual('Mobile', user.first_name)
        self.assertEqual(True, user.is_active)
        self.assertEqual(True, user.is_provisioned)
        # confirm user can login
        self.assertEqual(True, self.client.login(username='mw1', password='s3cr4t'))

    def test_create_unprovisioned(self):
        user = CommCareUser.create(
            self.domain,
            'mw1',
            's3cr4t',
            email='mw1@example.com',
            is_provisioned=False,
        )
        self.addCleanup(user.delete)
        self.assertEqual(False, user.is_active)
        self.assertEqual(False, user.is_provisioned)
        # confirm user can't login

        django_user = user.get_django_user()
        self.assertEqual(False, django_user.is_active)
        self.assertEqual(False, self.client.login(username='mw1', password='s3cr4t'))

    def test_is_active_overrides_is_provisioned(self):
        user = CommCareUser.create(
            self.domain,
            'mw1',
            's3cr4t',
            email='mw1@example.com',
            is_active=True,
            is_provisioned=False,
        )
        self.addCleanup(user.delete)
        self.assertEqual(True, user.is_active)
        self.assertEqual(False, user.is_provisioned)
        # confirm user can login
        django_user = user.get_django_user()
        self.assertEqual(True, django_user.is_active)
        self.assertEqual(True, self.client.login(username='mw1', password='s3cr4t'))
