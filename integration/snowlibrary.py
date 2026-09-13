"""
ServiceNow API Client Library
===============================
Provides a wrapper around the ServiceNow Table API (REST).

Capabilities:
  - Basic or OAuth authentication (configured via config.json).
  - Create, Update, and Read records on any ServiceNow table.
  - Unified syncRecord() method that auto-selects create vs update
    based on whether a sys_id is provided.
"""

import requests
import json


class servicenow:
    """Client for interacting with the ServiceNow Table API.

    On instantiation the client:
      1. Loads connection settings from config.json.
      2. Sets up authentication credentials (basic or OAuth).
    """

    def __init__(self):
        # Load shared configuration (ServiceNow URL, credentials, auth mode)
        with open('integration/config.json') as file:
            config = json.load(file)
        self.config = config

        # Standard headers for JSON request/response
        self.headers = {"Content-Type":"application/json","Accept":"application/json"}

        # Configure authentication based on the method specified in config
        if(self.config["snow"]["auth"] == "basic"):
            # HTTP Basic Auth — username:password tuple
            self.auth = (self.config["snow"]["username"], self.config["snow"]["password"])
        elif(self.config["snow"]["auth"] == "oauth"):
            # OAuth — placeholder; currently falls back to basic credentials
            self.auth = (self.config["snow"]["username"], self.config["snow"]["password"])

    def createRecord(self, tableName, payload):
        """Create a new record in the specified ServiceNow table.

        Args:
            tableName: ServiceNow table name (e.g., 'sn_grc_issue').
            payload:   Dict of field name → value pairs for the new record.
        """
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}'
        response = requests.post(url=url, 
                                auth=self.auth, 
                                headers=self.headers, 
                                data=json.dumps(payload))
        print(response.json())

    def updateRecord(self, tableName, sysid, payload):
        """Update an existing ServiceNow record identified by sys_id.

        Uses PATCH for partial updates (only the fields in payload are changed).

        Args:
            tableName: ServiceNow table name.
            sysid:     The sys_id of the record to update.
            payload:   Dict of field name → new value pairs.
        """
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}/{sysid}'
        response = requests.patch(url=url, 
                                auth=self.auth, 
                                headers=self.headers, 
                                data=json.dumps(payload))
        print(response.json())

    def syncRecord(self, tableName, payload, sysid=None):
        """Create or update a ServiceNow record (unified upsert method).

        If sysid is provided → PATCH (update); otherwise → POST (create).
        Returns the sys_id of the created/updated record.

        Args:
            tableName: ServiceNow table name (e.g., 'sn_grc_issue').
            payload:   Dict of field name → value pairs.
            sysid:     Optional sys_id for an existing record. If None, creates new.

        Returns:
            str: The sys_id of the resulting ServiceNow record.
        """
        config = self.config["snow"]

        if(sysid is None):
            # No sys_id → CREATE a new record via POST
            url = f'{config["url"]}/api/now/table/{tableName}'
            response = requests.post(url=url, 
                                auth=self.auth, 
                                headers=self.headers, 
                                data=json.dumps(payload))
        else:
            # sys_id provided → UPDATE the existing record via PATCH
            url = f'{config["url"]}/api/now/table/{tableName}/{sysid}'
            response = requests.patch(url=url, 
                                auth=self.auth, 
                                headers=self.headers, 
                                data=json.dumps(payload))

        result = response.json()
        return result["result"]["sys_id"]

    def getRecords(self, tableName, query='', field=''):
        """Retrieve records from a ServiceNow table with optional filtering.

        Args:
            tableName: ServiceNow table name to query.
            query:     Optional encoded query string (sysparm_query).
            field:     Optional comma-separated field list (sysparm_fields)
                       to limit the columns returned.
        """
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}'

        # Append query parameters based on which filters are provided
        if(query != '' and field != ''):
            url = url+f'?sysparm_query={query}&sysparm_fields={field}'
        elif(query != ''):
            url = url+f'?sysparm_query={query}'
        elif(field != ''):
            url = url+f'?sysparm_fields={field}'

        response = requests.get(url=url,
                                auth=self.auth,
                                headers=self.headers)
        print(len(response.json()["result"]))        