"""
Archer API Client Library
==========================
Provides a wrapper around the RSA Archer GRC Platform REST and SOAP APIs.

Capabilities:
  - Session-based authentication via the Platform API.
  - Create / Update content records via the Platform API.
  - Retrieve records from a saved Archer report (SOAP SearchRecordsByReport),
    with automatic pagination to fetch all pages.
"""

import requests
import json
import xmltodict


class archer:
    """Client for interacting with the RSA Archer GRC platform.

    On instantiation the client:
      1. Loads connection settings from config.json.
      2. Authenticates and stores a reusable session token.
    """

    def __init__(self):
        # Load shared configuration (Archer URL, credentials, field mappings)
        with open('integration/config.json') as file:
            config = json.load(file)
        self.config = config

        # Authenticate immediately so the session token is ready for use
        self.sessionToken = self.authenticate()

    def authenticate(self):
        """Authenticate against the Archer Platform API and return a session token.

        Uses the /platformapi/core/security/login endpoint with instance name,
        username, domain, and password from config.
        """
        baseURL = self.config['archer']['url']
        url = f"{baseURL}/platformapi/core/security/login"
        headers = {"Content-Type": "application/json"}

        # Build the login request body from config values
        requestBody = {
                        "InstanceName":self.config['archer']['instance'],
                        "Username":self.config['archer']['username'],
                        "UserDomain":self.config['archer']['domain'],
                        "Password":self.config['archer']['password']
                        }

        response = requests.post(url=url, headers=headers, json=requestBody)
        resp = response.json()

        # Extract the session token from the API response
        SessionToken = resp['RequestedObject']['SessionToken']
        return SessionToken

    def syncRecord(self, payload, method='create'):
        """Create or update an Archer content record via the Platform API.

        Args:
            payload: JSON-serialisable dict conforming to the Archer content schema.
            method:  'create' (POST) or 'update' (PUT). Defaults to 'create'.
        """
        baseURL = self.config['archer']['url']
        url = f"{baseURL}/platformapi/core/content"

        # Attach the session token in the Archer-specific Authorization header
        headers = {
            'Authorization': f'Archer session-id="{self.sessionToken}"',
            'Content-Type': 'application/json'
            }

        if(method == 'create'):
            response = requests.post(url, headers=headers, data=json.dumps(payload))
        elif(method == 'update'):
            response = requests.put(url, headers=headers, data=json.dumps(payload))

    def getDataFromArcher(self):
        """Fetch ALL records from the configured Archer report, handling pagination.

        Returns:
            list: A list of record dicts extracted from the report across all pages.
        """
        # Fetch the first page and determine how many pages exist
        data = self.SearchRecordsByReport()
        finalData = data["reportData"]["Records"]["Record"]
        iterations = data["iterations"]
        print(iterations)

        # If more than one page, loop through remaining pages and merge results
        if(iterations > 1):
            iterations += 2
            for i in range(2, iterations):
                reportData = self.SearchRecordsByReport(pageNumber=i)
                iterationData = reportData["reportData"]["Records"]["Record"]
                finalData.extend(iterationData)

        print(f"Final data set count - {len(finalData)}")
        return finalData

    def SearchRecordsByReport(self, pageNumber = 1):
        """Retrieve a single page of records from an Archer report (SOAP endpoint).

        Uses the /ws/search.asmx/SearchRecordsByReport SOAP service.
        The raw XML response is converted to a Python dict via xmltodict.

        Args:
            pageNumber: 1-based page index. Defaults to 1 (first page).

        Returns:
            dict with keys:
              - 'iterations': number of full pages available (totalRecords // pageSize).
              - 'reportData': parsed report content as a nested dict.
        """
        config = self.config
        reportId = config["mapping"]["as"]["reportid"]
        baseURL = self.config['archer']['url']
        url = f"{baseURL}/ws/search.asmx/SearchRecordsByReport"

        # Form-encoded payload required by the SOAP endpoint
        payload = f'sessionToken={self.sessionToken}&reportIdOrGuid={reportId}&pageNumber={pageNumber}'
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, headers=headers, data=payload)

        # --- Two-pass XML → JSON conversion ---
        # 1st pass: parse the SOAP envelope (outer XML wrapper)
        dataDict = xmltodict.parse(response.text)
        jsonData = json.loads(json.dumps(dataDict))

        # 2nd pass: parse the inner XML payload embedded in the <string> element
        dataDict2 = xmltodict.parse(jsonData["string"]["#text"])
        reportData = json.loads(json.dumps(dataDict2))

        # Calculate pagination metadata
        totalRecords = int(reportData["Records"]["@count"])
        currentReportRecords = len(reportData["Records"]["Record"])
        iterations = totalRecords // currentReportRecords

        return {"iterations":iterations, "reportData":reportData}
