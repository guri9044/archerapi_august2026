import requests
import csv

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

with open("users.csv", mode="r", encoding="utf-8-sig") as file:
    users = list(csv.DictReader(file))
createUserURL = f"{baseURL}/platformapi/core/system/user"
headers = {
"Authorization": "Archer session-id=" + SessionToken
}
for user in users:
    input = {
        "User":
        {
            "UserName":user['Username'],
            "FirstName":user['FirstName'],
            "LastName":user['LastName']
        },
        "Password":user['Password']
        }
    response = requests.post(url=createUserURL, headers=headers, json=input)
    if(response.status_code != 200):
        print("Failed to create user:", user['Username'], "Response:", response.status_code, response.text)
    else:
        resp = response.json()
        if(resp['IsSuccessful']):
            print("Successfully created user:", user['Username'], "Response:", resp)
            userid = resp['RequestedObject']['Id']
            groups = user['Group'].split('/')
            for group in groups:
                addUserToGroupURL = f"{baseURL}/platformapi/core/system/usergroup"
                addUsertoGroupInput = {
                        "UserId": int(userid),
                        "GroupId": int(group),
                        "IsAdd": True
                }
                response = requests.put(url=addUserToGroupURL, headers=headers, json=addUsertoGroupInput)
                if(response.status_code != 200):
                    print("Failed to add user:", user['Username'], "to group:", group, "Response:", response.status_code, response.text)
                else:
                    resp = response.json()
                    if(resp['IsSuccessful']):
                        print("Successfully added user:", user['Username'], "to group:", group)
                    else:
                        print("Failed to add user:", user['Username'], "to group:", group, "Response:", resp)
        else:
            print("Failed to create user:", user['Username'], "Response:", resp)