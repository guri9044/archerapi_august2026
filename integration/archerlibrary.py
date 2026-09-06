import requests
import json
import xmltodict

class archer:
    def __init__(self):
        with open('integration/config.json') as file:
            config = json.load(file)
        self.config = config
        self.sessionToken = self.authenticate()
        #print(self.sessionToken)

    def authenticate(self):
        baseURL = self.config['archer']['url']
        url = f"{baseURL}/platformapi/core/security/login"
        headers = {"Content-Type": "application/json"}
        requestBody = {
                        "InstanceName":self.config['archer']['instance'],
                        "Username":self.config['archer']['username'],
                        "UserDomain":self.config['archer']['domain'],
                        "Password":self.config['archer']['password']
                        }
        response = requests.post(url=url, headers=headers, json=requestBody)
        resp = response.json()
        SessionToken = resp['RequestedObject']['SessionToken']
        #print(SessionToken)
        return SessionToken

    def createRecord(self, jsonbody):
        print('')

    def getDataFromArcher(self):
        print('data')