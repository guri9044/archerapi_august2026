import requests
import json

class servicenow:
    def __init__(self):
        with open('integration/config.json') as file:
            config = json.load(file)
        self.config = config
        self.headers = {"Content-Type":"application/json","Accept":"application/json"}
        if(self.config["snow"]["auth"] == "basic"):
            self.auth = (self.config["snow"]["username"], self.config["snow"]["password"])
        elif(self.config["snow"]["auth"] == "oauth"):
            self.auth = (self.config["snow"]["username"], self.config["snow"]["password"])

    def createRecord(self, tableName, payload):
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}'
        response = requests.post(url=url, 
                                auth=self.auth, 
                                headers=self.headers, 
                                data=json.dumps(payload))
        print(response.json())

    def updateRecord(self, tableName, sysid, payload):
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}/{sysid}'
        response = requests.patch(url=url, 
                                auth=self.auth, 
                                headers=self.headers, 
                                data=json.dumps(payload))
        print(response.json())

    def getRecords(self, tableName, query='', field=''):
        config = self.config["snow"]
        url = f'{config["url"]}/api/now/table/{tableName}'
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