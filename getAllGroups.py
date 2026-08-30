import requests

baseURL = "https://archer-irm.com/archer"
url = f"{baseURL}/platformapi/core/security/login"
headers = {"Content-Type": "application/json"}
requestBody = {
                "InstanceName":"t202603",
                "Username":"trainer",
                "UserDomain":"",
                "Password":"Archer@123"
                }
response = requests.post(url=url, headers=headers, json=requestBody)
resp = response.json()
SessionToken = resp['RequestedObject']['SessionToken']


url = f"{baseURL}/platformapi/core/system/group"
headers = {
    "Authorization": "Archer session-id=" + SessionToken,
    "X-Http-Method-Override": "GET"
}
response = requests.post(url=url, headers=headers)
respStatusCode = response.status_code
if(respStatusCode != 200):
    print("Failed to retrieve groups")
    exit()
groups = response.json()
for group in groups:
    id = group['RequestedObject']['Id']
    name = group['RequestedObject']['Name']
    print(f"Group ID: {id}, Group Name: {name}")