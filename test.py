import requests
import xmltodict

resp = requests.get(
    url='https://catfact.ninja/fact',
    headers={'accept': 'application/json'
    })
respStatus = resp.status_code
if(respStatus == 200):
    print('Request susscessful')
    respValue = resp.json()
    print(respValue['fact'])
    print()
else:
    print('Request failed')