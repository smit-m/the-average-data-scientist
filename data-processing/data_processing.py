import sys
sys.path.append('tools')

import requests
from time import time
from pprint import pprint
from urllib.parse import quote_plus
from db_connect import get_col2


def get_comploc(raw_data:list):
    return set((item['Location'], item['Company']) for item in raw_data
               if 'Location' in item and 'Company' in item)


col1 = ['calvin-vpn1.v4.softether.net:443', 'JL_Scraping', 'DS_RawData']
col2 = ['calvin-vpn1.v4.softether.net:443', 'JL_Scraping', 'DS_CompLoc']

with get_col2(col1).find({}) as d1, get_col2(col2).find({}) as d2:
    data_raw = list(d1)
    data_comploc = list(d2)
    pass

# for line in data_raw:
#     if '_id' in line:
#         line.pop('_id')
#     if 'Description' in line:
#         line.pop('Description')
#     pass
# with open('/home/windr/data/data1.json', 'w') as fh:
#     json.dump(data_raw, fh)
#     pass


# GCP Geocoding API #
geoc_url = "https://maps.googleapis.com/maps/api/geocode/json?address={ADDR}+CA&key={MAK}"
mak = 'AIzaSyAZGqyFItxx5pklWngb7-PmrvueLQpwmBM'
# qaddr = 'New York, NY 10036 Bank of America'
# with requests.get(geoc_url.format(ADDR=quote_plus(qaddr), MAK=mak)) as r:
#     result = r.json()
#     # pprint(result['results'][0]['formatted_address'])
#     pprint(result)
#     pass

comploc_raw = get_comploc(data_raw)
comploc = get_comploc(data_comploc)

dti = list({'Location': cl[0], 'Company': cl[1]} for cl in comploc_raw if cl not in comploc)
if len(dti) > 0:
    get_col2(col2).insert_many(dti)

# t = time()
# for item in list(comploc_raw)[200:250]:
#     qaddr =  f'{item[0]} {item[1]}'
#     with requests.get(geoc_url.format(ADDR=quote_plus(qaddr), MAK=mak)) as r:
#         if r.status_code == 200:
#             res = r.json()
#             # pprint(r.json()['results'][0]['formatted_address'])
#             pprint((qaddr, res['results'][0]['formatted_address'],
#                     res['results'][0]['geometry']['location']))
#             print()
#         else:
#             print('bad response')
#     pass
# print(f'\r\nrun time: {time() - t} seconds')

# get_col2(col2).insert_many(list({'Location': item[0], 'Company': item[1]} for item in comploc_raw))

counter = 0
for line in data_comploc:
    counter += 1
    if len(line) == 3:
        qaddr = f"{line['Company']} {line['Location']}"
        with requests.get(geoc_url.format(ADDR=quote_plus(qaddr), MAK=mak)) as r:
            res = r.json()
            if r.status_code == 200 and len(res['results']) > 0:
                dti = {'formatted_address': res['results'][0]['formatted_address'],
                       'lat': res['results'][0]['geometry']['location']['lat'],
                       'lng': res['results'][0]['geometry']['location']['lng']}
        get_col2(col2).update_one({'_id': line['_id']}, {'$set': dti})
        pprint((counter, dti['formatted_address']))
    pass
