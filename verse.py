from bs4 import BeautifulSoup
import requests


bezel = '\n' + '#' * 50 + '\n'

err_msg = f'{bezel}Could not fetch daily verse. No internet? Hiccups on dailyverses.net?{bezel}'

url = 'https://dailyverses.net/random-bible-verse'

try:
    response = requests.get(url)
except (requests.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException):
    print(err_msg)

if response.status_code != 200:
    print(err_msg)

soup = BeautifulSoup(response.content, features='html.parser')
txt = soup.find_all('span', 'v1')[0].get_text()
source = soup.find_all('a', 'vc')[0].get_text()
formatted_source = f' ({source})'

print(bezel, txt, formatted_source, bezel, sep='')

