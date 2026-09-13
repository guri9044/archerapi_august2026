"""
Archer ↔ ServiceNow Integration - Main Orchestrator
=====================================================
Syncs Archer Findings (GRC) to ServiceNow Issues (sn_grc_issue).

Workflow:
  1. Authenticate with Archer and ServiceNow.
  2. Pull all Finding records from an Archer report.
  3. Map Archer fields → ServiceNow fields using config-driven mapping.
  4. Create or update the corresponding ServiceNow Issue record.
  5. Write the ServiceNow sys_id back into the Archer record for traceability.
"""

import json
from archerlibrary import archer
from snowlibrary import servicenow

# --- Initialise API clients (authentication happens inside constructors) ---
arch = archer()
snow = servicenow()

# Load the shared configuration (field mapping, connection details, etc.)
with open('integration/config.json') as file:
    config = json.load(file)

# Retrieve all Archer Finding records via the configured report
archerReportData = arch.getDataFromArcher()

# --- Process each Archer record and sync to ServiceNow ---
for record in archerReportData:
    # Content ID uniquely identifies the Archer record
    archerFindingTrackingId = record["@contentId"]

    # "as" = Archer → ServiceNow direction; load field-level mapping rules
    asmap = config["mapping"]["as"]["fields"]
    snowInput = {}  # Payload that will be sent to the ServiceNow API

    # --- Field-level transformation ---
    for fieldData in record["Field"]:
        fieldId = int(fieldData["@id"])

        # Find the mapping entry that matches this Archer field ID
        mapObj = next((m for m in asmap if int(m["archerFieldId"]) == fieldId), None)

        if(mapObj is not None):
            snowField = mapObj["snowField"]

            # Type 4 = Values List field → requires value translation via lookup map
            if(int(mapObj["archerFieldType"]) == 4):
                archerValue = fieldData["ListValues"]["ListValue"]["#text"]
                targetSnowValue = mapObj["values"][archerValue]
                input = targetSnowValue
            else:
                # Text / Numeric / other field types → pass value through directly
                input = fieldData["#text"]

            snowInput[snowField] = input

    # Build a clickable Archer deep-link URL for the Finding record
    archerURL = f"https://archer-irm.com/Archer/Default.aspx?requestUrl=..%2fGenericContent%2fRecord.aspx%3fid%3d{archerFindingTrackingId}%26moduleId%3d167"
    snowInput["u_archer_issue_link"] = f"<a target='_blank' href='{archerURL}'>{archerFindingTrackingId}</a>"

    # Locate the ServiceNow sys_id field stored in Archer (used to decide create vs update)
    snowSysIdField = next((s for s in record["Field"] if int(s["@id"]) == int(config["mapping"]["as"]["targetKeyField"])), None)
    
    if "#text" in snowSysIdField:
        # --- UPDATE path: Archer already has a linked ServiceNow sys_id ---
        print(f'Archer record mapped in ServiceNow - {snowSysIdField["#text"]}')
        snowSysId = snow.syncRecord(tableName='sn_grc_issue', payload=snowInput, sysid=snowSysIdField["#text"])
    else:
        # --- CREATE path: No ServiceNow record exists yet ---
        print('Archer record not mapped in ServiceNow')
        snowSysId = snow.syncRecord(tableName='sn_grc_issue', payload=snowInput)

        # Write the new ServiceNow sys_id back into Archer for future sync cycles
        archerUpdateJSON = {"Content": {
        "Id": archerFindingTrackingId,
        "LevelId": config["mapping"]["as"]["levelId"],
        "FieldContents": {"28824": {"Type": 1,"Value": snowSysId,"FieldId": 28824}}}}
        arch.syncRecord(payload=archerUpdateJSON, method='update')

# --- Future / Planned Integration (ServiceNow → Archer) ---
# ServiceNow - Archer Integration (sync ServiceNow Remediation Tasks to Archer Remediation plan, ensuring Archer Remediation plan is mapped to Archer Finding)
# get data from servicenow
# transform servicenow json data to archer api input format
# reuse archer authentication token
# api call to archer - create/update records
# update archer tracking in ServiceNow