from django.test import TestCase
import os
from casexml.apps.case.models import CommCareCase
from couchforms.util import post_xform_to_couch
from casexml.apps.case.signals import process_cases
from datetime import datetime

class Version2CaseParsingTest(TestCase):
    """
    Tests parsing v2 casexml
    """
    
    def setUp(self):
        for item in CommCareCase.view("case/by_xform_id", include_docs=True).all():
            item.delete()
        
    
    def testParseCreate(self):
        file_path = os.path.join(os.path.dirname(__file__), "data", "v2", "basic_create.xml")
        with open(file_path, "rb") as f:
            xml_data = f.read()
        
        form = post_xform_to_couch(xml_data)
        # pdb.set_trace()
        process_cases(sender="testharness", xform=form)
        case = CommCareCase.get("foo-case-id")
        self.assertEqual("bar-user-id", case.user_id)
        self.assertEqual(datetime(2011, 12, 8, 13, 42, 50), case.modified_on)
        self.assertEqual("v2_case_type", case.type)
        