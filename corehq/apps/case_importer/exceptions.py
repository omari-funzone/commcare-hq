from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy, ugettext_noop
import xlrd


class ImporterError(Exception):
    """
    Generic error raised for any problem to do with finding, opening, reading, etc.
    the file being imported

    When possible, a more specific subclass should be used
    """


class ImporterFileNotFound(ImporterError):
    """Raised when a referenced file can't be found"""


class ImporterRefError(ImporterError):
    """Raised when a Soil download ref is None"""


class ImporterExcelError(ImporterError, xlrd.XLRDError):
    """
    Generic error raised for any error parsing an Excel file

    When possible, a more specific subclass should be used
    """


class ImporterExcelFileEncrypted(ImporterExcelError):
    """Raised when a file cannot be open because it is encrypted (password-protected)"""


class InvalidCustomFieldNameException(ImporterError):
    """Raised when a custom field name is reserved (e.g. "type")"""
    pass


class CaseRowError(Exception):
    """Base Error class for failures associated with an individual upload row"""
    title = ""
    message = ""

    def __init__(self, row_number, column_name=None):
        self.row_number = row_number
        self.column_name = column_name
        super(CaseRowError, self).__init__(self.message)


class InvalidOwnerName(CaseRowError):
    title = ugettext_noop('Invalid Owner Name')
    message = ugettext_lazy(
        "Owner name was used in the mapping but there were errors when "
        "uploading because of these values."
    )


class InvalidOwnerId(CaseRowError):
    title = ugettext_noop('Invalid Owner ID')
    message = ugettext_lazy(
        "Owner ID was used in the mapping but there were errors when "
        "uploading because of these values. Make sure the values in this "
        "column are ID's for users or case sharing groups or locations."
    )


class InvalidParentId(CaseRowError):
    title = ugettext_noop('Invalid Parent ID')
    message = ugettext_lazy(
        "An invalid or unknown parent case was specified for the "
        "uploaded case."
    )


class InvalidDate(CaseRowError):
    title = ugettext_noop('Invalid Date')
    message = ugettext_lazy(
        "Date fields were specified that caused an error during "
        "conversion. This is likely caused by a value from Excel having "
        "the wrong type or not being formatted properly."
    )


class BlankExternalId(CaseRowError):
    title = ugettext_noop('Blank External ID')
    message = ugettext_lazy(
        "Blank external ids were found in these rows causing as error "
        "when importing cases."
    )


class CaseGeneration(CaseRowError):
    title = ugettext_noop('Case Generation Error')
    message = ugettext_lazy(
        "These rows failed to generate cases for unknown reasons"
    )


class DuplicateLocationName(CaseRowError):
    title = ugettext_noop('Duplicated Location Name')
    message = ugettext_lazy(
        "Owner ID was used in the mapping, but there were errors when "
        "uploading because of these values. There are multiple locations "
        "with this same name, try using site-code instead."
    )


class InvalidInteger(CaseRowError):
    title = ugettext_noop('Invalid Integer')
    message = ugettext_lazy(
        "Integer values were specified, but the values in Excel were not "
        "all integers"
    )


class ImportErrorMessage(CaseRowError):
    title = ugettext_noop('Import Error')
    message = ugettext_lazy(
        "Problems in importing cases. Please check the Excel file."
    )
