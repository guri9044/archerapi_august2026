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
import logging
import datetime
import os

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
        currentDate = datetime.datetime.now().strftime("%Y.%m.%d")
        logFileName = os.path.join("integration","logs",f"ServiceNow.Integration.Log.{currentDate}.log")
        '''self.logger = logging.getLogger(__name__)
        loggerHandler = logging.FileHandler(logFileName)
        loggerHandler.setLevel(logging.INFO)
        loggerHandler.setFormatter(logging.Formatter("[%(levelname)s] - %(message)s"))
        self.logger.addHandler(loggerHandler)
        self.logger.info('servicenow api initiated...')'''
        logging.basicConfig(
            filename=logFileName,
            filemode="a",
            level=logging.INFO,
            format="[%(levelname)s] - %(message)s"
        )
        # Standard headers for JSON request/response
        self.headers = {"Content-Type":"application/json","Accept":"application/json"}

        # Configure authentication based on the method specified in config
        if(self.config["snow"]["auth"] == "basic"):
            # HTTP Basic Auth — username:password tuple
            self.auth = (self.config["snow"]["username"], self.config["snow"]["password"])
        elif(self.config["snow"]["auth"] == "oauth"):
            # OAuth — placeholder; currently falls back to basic credentials
            self.auth = (self.config["snow"]["username"], self.config["snow"]["password"])

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
        logging.info('servicenow api initiated...')
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
        #print(result)  # Uncomment to debug the full API response payload
        return result["result"]["sys_id"]

    def getRecords(self, tableName, query='', fields=''):
        """Retrieve records from a ServiceNow table with optional filtering.

        Args:
            tableName: ServiceNow table name to query.
            query:     Optional encoded query string (sysparm_query).
            fields:    Optional comma-separated field list (sysparm_fields)
                       to limit the columns returned.

        Returns:
            list: List of record dicts from the 'result' array of the API response.
        """
        logging.info('servicenow api initiated...')
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}'

        # Append query parameters based on which filters are provided
        if(query != '' and fields != ''):
            url = url+f'?sysparm_query={query}&sysparm_fields={fields}'
        elif(query != ''):
            url = url+f'?sysparm_query={query}'
        elif(fields != ''):
            url = url+f'?sysparm_fields={fields}'

        response = requests.get(url=url,
                                auth=self.auth,
                                headers=self.headers)
        #print(response)  # Uncomment to debug the raw HTTP response object
        print(len(response.json()["result"]))   # Log total record count fetched
        return response.json()["result"]     