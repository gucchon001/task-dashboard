import requests

print('requests imported successfully')
response = requests.get('https://httpbin.org/get')
print('Status code:', response.status_code)
print('Response:', response.json()) 