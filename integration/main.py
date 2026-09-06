from re import search
import json
import requests
from archerlibrary import archer
from snowlibrary import servicenow

#arch = archer()
#arch.getDataFromArcher()

snowInput = {
    "short_description":"finding name",
    "description":"finding description",
    "state":"1",
    "priority":"3",
    "classification":"3"
    }

snow = servicenow()
#snow.createRecord(tableName='sn_grc_issue', payload=snowInput)

query = 'priority=4^sys_updated_on>=javascript:gs.beginningOfYesterday()'
fields = 'short_description,description,priority,state'
snow.getRecords(tableName='sn_grc_issue', field=fields, query=query)
# Archer - ServiceNow Integration (sync Archer Findings to ServiceNow Issues)
# authenticate in archer
# get data from archer report
# convert xml data to json
# transform archer json data to snow api input format
# api call to snow - create/update records
# update servicenow sysid back in Archer


# ServiceNow - Archer Integration (sync ServiceNow Remediation Tasks to Archer Remediation plan, ensuring Archer Remediation plan is mapped to Archer Finding)
# get data from servicenow
# transform servicenow json data to archer api input format
# reuse archer authentication token
# api call to archer - create/update records
# update archer tracking in ServiceNow