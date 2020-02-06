from schema import Optional as SchemaOptional
from schema import Regex


id_schema = Regex(r"^[A-Za-z0-9]+$")
# DHIS2 accepts date values, but returns datetime values for dates:
date_schema = Regex(r"^\d{4}-\d{2}-\d{2}(:?T\d{2}:\d{2}:\d{2}.\d{3})?$")
datetime_schema = Regex(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}$")
enrollment_status_schema = Regex("^(ACTIVE|COMPLETED|CANCELED)$")
event_status_schema = Regex("^(ACTIVE|COMPLETED|VISITED|SCHEDULE|OVERDUE|SKIPPED)$")


def get_event_schema() -> dict:
    """
    Returns the schema for a DHIS2 Event.

    >>> event = {
    ...   "program": "eBAyeGv0exc",
    ...   "orgUnit": "DiszpKrYNg8",
    ...   "eventDate": "2013-05-17",
    ...   "status": "COMPLETED",
    ...   "completedDate": "2013-05-18",
    ...   "storedBy": "admin",
    ...   "coordinate": {
    ...     "latitude": 59.8,
    ...     "longitude": 10.9
    ...   },
    ...   "dataValues": [
    ...     { "dataElement": "qrur9Dvnyt5", "value": "22" },
    ...     { "dataElement": "oZg33kd9taw", "value": "Male" },
    ...     { "dataElement": "msodh3rEMJa", "value": "2013-05-18" }
    ...   ]
    ... }
    >>> Schema(get_event_schema()).is_valid(event)
    True

    """
    relationship_schema = get_relationship_schema()
    return {
        SchemaOptional("assignedUser"): id_schema,
        SchemaOptional("attributeCategoryOptions"): id_schema,
        SchemaOptional("attributeOptionCombo"): id_schema,
        SchemaOptional("completedDate"): date_schema,
        SchemaOptional("coordinate"): {
            "latitude": float,
            "longitude": float,
        },
        SchemaOptional("created"): datetime_schema,
        SchemaOptional("createdAtClient"): datetime_schema,
        "dataValues": [{
            SchemaOptional("created"): datetime_schema,
            "dataElement": id_schema,
            SchemaOptional("lastUpdated"): datetime_schema,
            SchemaOptional("providedElsewhere"): bool,
            SchemaOptional("storedBy"): str,
            "value": object,
        }],
        SchemaOptional("deleted"): bool,
        SchemaOptional("dueDate"): date_schema,
        SchemaOptional("enrollment"): id_schema,
        SchemaOptional("enrollmentStatus"): enrollment_status_schema,
        SchemaOptional("event"): id_schema,
        "eventDate": date_schema,
        SchemaOptional("geometry"): {
            "type": str,
            "coordinates": [float],
        },
        SchemaOptional("lastUpdated"): datetime_schema,
        SchemaOptional("lastUpdatedAtClient"): datetime_schema,
        SchemaOptional("notes"): list,
        "orgUnit": id_schema,
        SchemaOptional("orgUnitName"): str,
        "program": id_schema,
        SchemaOptional("programStage"): id_schema,
        SchemaOptional("relationships"): [relationship_schema],
        SchemaOptional("status"): event_status_schema,
        SchemaOptional("storedBy"): str,
        SchemaOptional("trackedEntityInstance"): id_schema,
    }


def get_relationship_schema() -> dict:
    return {
        "relationshipType": id_schema,
        SchemaOptional("relationshipName"): str,
        SchemaOptional("relationship"): id_schema,
        SchemaOptional("bidirectional"): bool,
        "from": {
            "trackedEntityInstance": {
                "trackedEntityInstance": id_schema,
            }
        },
        "to": {
            "trackedEntityInstance": {
                "trackedEntityInstance": id_schema,
            }
        },
        SchemaOptional("created"): datetime_schema,
        SchemaOptional("lastUpdated"): datetime_schema,
    }


def get_tracked_entity_schema() -> dict:
    """
    Returns the schema of a tracked entity instance.
    """
    event_schema = get_event_schema()
    relationship_schema = get_relationship_schema()
    return {
        SchemaOptional("attributes"): [{
            "attribute": id_schema,
            SchemaOptional("code"): str,
            SchemaOptional("created"): datetime_schema,
            SchemaOptional("displayName"): str,
            SchemaOptional("lastUpdated"): datetime_schema,
            SchemaOptional("storedBy"): str,
            "value": object,
            SchemaOptional("valueType"): str,
        }],
        SchemaOptional("created"): datetime_schema,
        SchemaOptional("createdAtClient"): datetime_schema,
        SchemaOptional("deleted"): bool,
        SchemaOptional("enrollments"): [{
            "program": id_schema,
            SchemaOptional("orgUnit"): id_schema,
            SchemaOptional("enrollmentDate"): date_schema,
            SchemaOptional("incidentDate"): date_schema,
            SchemaOptional("events"): [event_schema],
        }],
        SchemaOptional("featureType"): str,
        SchemaOptional("geometry"): {
            "type": str,
            "coordinates": [float],
        },
        SchemaOptional("inactive"): bool,
        SchemaOptional("lastUpdated"): datetime_schema,
        SchemaOptional("lastUpdatedAtClient"): datetime_schema,
        "orgUnit": id_schema,
        SchemaOptional("programOwners"): [object],
        SchemaOptional("relationships"): [relationship_schema],
        SchemaOptional("trackedEntityInstance"): id_schema,
        "trackedEntityType": id_schema,
    }
