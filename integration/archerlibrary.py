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
import logging
import datetime
import os

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
        currentDate = datetime.datetime.now().strftime("%Y.%m.%d")
        logFileName = os.path.join("integration","logs",f"Archer.Integration.Log.{currentDate}.log")
        '''self.logger = logging.getLogger(__name__)
        loggerHandler = logging.FileHandler(logFileName)
        loggerHandler.setLevel(logging.INFO)
        loggerHandler.setFormatter(logging.Formatter("[%(levelname)s] - %(message)s"))
        self.logger.addHandler(loggerHandler)'''
        logging.basicConfig(
            filename=logFileName,
            filemode="a",
            level=logging.INFO,
            format="[%(levelname)s] - %(message)s"
        )
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
        responseCode = response.status_code
        if(responseCode != 200):
            logging.info(f'[Archer] Unable to authenticate - {response.text}')
            print(f'[Archer] Unable to authenticate - {response.text}')
            exit()
        else: 
            resp = response.json()
            if(resp['IsSuccessful']):
            # Extract the session token from the API response
                logging.info(f'[Archer] authentication done')
                SessionToken = resp['RequestedObject']['SessionToken']
                return SessionToken
            else:
                logging.critical(f'[Archer] Unable to authenticate - {resp["ValidationMessages"]}')
                print(f'[Archer] Unable to authenticate - {resp["ValidationMessages"]}')
                exit()

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
        responseCode = response.status_code
        if(responseCode != 200):
            print(f'[Archer] Unable to {method} record - {response.text}')
            logging.error(f'[Archer] Unable to {method} record - {response.text}')
        else: 
            resp = response.json()
            print(resp)
            if(resp['IsSuccessful']):
                return response
            else:
                print(f'[Archer] Unable to {method} record - {resp["ValidationMessages"]}')
                logging.error(f'[Archer] Unable to {method} record - {resp["ValidationMessages"]}')

    def getDataFromArcher(self):
        """Fetch ALL records from the configured Archer report, handling pagination.

        Returns:
            list: A list of record dicts extracted from the report across all pages.
        """
        # Fetch the first page and determine how many pages exist
        data = self.SearchRecordsByReport()
        finalData = data["reportData"]["Records"]["Record"]
        iterations = data["iterations"]
        #print(iterations)

        # If more than one page, loop through remaining pages and merge results
        if(iterations > 1):
            # +2 accounts for: integer-division truncation (may drop last partial page)
            # and the fact that range(2, n) is exclusive of n (pages are 1-indexed).
            iterations += 2
            for i in range(2, iterations):
                reportData = self.SearchRecordsByReport(pageNumber=i)
                iterationData = reportData["reportData"]["Records"]["Record"]
                finalData.extend(iterationData)

        # Log the final merged record count before returning
        print(f"[Archer] Final data set count - {len(finalData)}")
        logging.info(f"[Archer] Final data set count - {len(finalData)}")
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
        responseCode = response.status_code
        if(responseCode != 200):
            print(f'[Archer] Unable to retrieve records from report {reportId} and page {pageNumber} - {response.text}')
            logging.error(f'[Archer] Unable to retrieve records from report {reportId} and page {pageNumber} - {response.text}')
        else: 
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
