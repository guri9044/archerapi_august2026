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
import os
import logging
import datetime

os.system('cls' if os.name == 'nt' else 'clear')
if not os.path.exists("integration/logs"):
    os.makedirs("integration/logs")

currentDate = datetime.datetime.now().strftime("%Y.%m.%d")
logFileName = os.path.join("integration","logs",f"Archer.ServiceNow.Integration.Log.{currentDate}.log")
logging.basicConfig(
    filename=logFileName,
    filemode="a",
    level=logging.INFO,
    format="[%(levelname)s] - %(message)s"
)

# --- Initialise API clients (authentication happens inside constructors) ---
arch = archer()
snow = servicenow()

# Load the shared configuration (field mapping, connection details, etc.)
with open('integration/config.json') as file:
    config = json.load(file)
    logging.info('config loaded')

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
    #archerURL = f"https://archer-irm.com/Archer/Default.aspx?requestUrl=..%2fGenericContent%2fRecord.aspx%3fid%3d{archerFindingTrackingId}%26moduleId%3d167"
    #snowInput["u_archer_issue_link"] = f"<a target='_blank' href='{archerURL}'>{archerFindingTrackingId}</a>"

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

        # Write the new ServiceNow sys_id back into Archer field 28824
        # ("ServiceNow Issue ID" text field) for traceability in future sync cycles
        archerUpdateJSON = {"Content": {
        "Id": archerFindingTrackingId,
        "LevelId": config["mapping"]["as"]["levelId"],
        "FieldContents": {"28824": {"Type": 1,"Value": snowSysId,"FieldId": 28824}}}}
        arch.syncRecord(payload=archerUpdateJSON, method='update')

# --- ServiceNow → Archer Integration (SA direction) ---
# Syncs ServiceNow Remediation Tasks (sn_grc_task) to Archer Remediation Plan records.
# Each ServiceNow task is linked back to its parent Archer Finding via u_archer_trackig_id.
# After creating a new Archer Remediation Plan, the Archer record ID is written back
# into the ServiceNow task (u_archer_remediation_plan_id) for future update cycles.
print("downloading snow data")
snowConfig = config['mapping']['sa']
snowRem = snow.getRecords(tableName=snowConfig["sourceTable"], query=snowConfig["sourceQuery"], fields=snowConfig["sourceFields"])
for rem in snowRem:
    archerJSONRequest = {"Content":{}}
    archerJSONRequest["Content"]["LevelId"] = snowConfig["targetLevelId"]
    archerJSONRequest["Content"]["FieldContents"] = {}
    for map in snowConfig["fields"]:
        if("snowField" in map):
            snowField = map["snowField"]
        archerFieldID = map["archerFieldId"]
        type = int(map["archerFieldType"])

        # --- Determine the Archer-formatted value for this field ---
        if("defaultValue" in map and "snowField" not in map):
            # Config-only default (no ServiceNow source field) — use static value
            if(type == 8):
                # Type 8 = Users/Groups List → wrap user ID in UserList structure
                targetValue = {"UserList": [{"Id": map["defaultValue"]}]}
            elif(type == 4):
                # Type 4 = Values List → wrap values list ID in ValuesListIds
                targetValue = {"ValuesListIds": [map["defaultValue"]]}
            elif(type == 2):
                # Type 2 = Numeric → cast to int
                targetValue = int(map["defaultValue"])
            else:
                # Type 1/3 = Text/Date → pass through as-is
                targetValue = map["defaultValue"]
        elif(type == 1 or type == 3):
            # Type 1 = Text, Type 3 = Date → pass string value; fall back to default if blank
            print(f"[DEBUG] Mapping text/date field archerFieldId={archerFieldID}")
            if(rem[snowField] == ''):
                rem[snowField] = map["defaultValue"]
            targetValue = rem[snowField]
        elif(type == 2):
            # Type 2 = Numeric → cast to int; fall back to default if blank
            print(f"[DEBUG] Mapping numeric field archerFieldId={archerFieldID}")
            if(rem[snowField] == ''):
                rem[snowField] = map["defaultValue"]
            targetValue = int(rem[snowField])
        elif(type == 4):
            # Type 4 = Values List → translate ServiceNow value to Archer values list ID via config map
            if(rem[snowField] == ''):
                rem[snowField] = map["defaultValue"]
            snowValue = rem[snowField]
            archerValue = map["values"][snowValue]
            targetValue = {"ValuesListIds": [archerValue]}
        elif(type == 9):
            # Type 9 = Cross-Reference → wrap the related content ID
            targetValue = [{"ContentId": int(rem[snowField])}]
        elif(type == 23):
            # Type 23 = Related Records (Tracking ID) → list of integer content IDs
            targetValue = [int(rem[snowField])]

        # Append this field's payload entry using Archer's FieldContents schema
        archerJSONRequest["Content"]["FieldContents"][str(archerFieldID)] = {
				"Type": type,
				"Value": targetValue,
				"FieldId": int(archerFieldID)
			}
    # Check whether this ServiceNow task already has a linked Archer Remediation Plan
    existingRemPlanId = rem['u_archer_remediation_plan_id']
    print(f'existingRemPlanId - {existingRemPlanId}')
    if(existingRemPlanId == ''):
        # --- CREATE path: No Archer Remediation Plan exists yet ---
        archerResponse = arch.syncRecord(payload=archerJSONRequest)
        archerId = archerResponse.json()["RequestedObject"]["Id"]
        # Write the new Archer record ID back into the ServiceNow task for future sync cycles
        snowRemJSON = {'u_archer_remediation_plan_id':archerId}
        snow.syncRecord(tableName='sn_grc_task', payload=snowRemJSON, sysid=rem['sys_id'])
    else:
        # --- UPDATE path: Archer Remediation Plan already exists, update in place ---
        archerJSONRequest["Content"]["Id"] = existingRemPlanId
        archerResponse = arch.syncRecord(payload=archerJSONRequest, method='update')