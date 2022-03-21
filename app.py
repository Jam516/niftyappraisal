#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import os
import sys
import json
import time
import datetime
import pandas as pd
import requests
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

NFTPORT_API_KEY=os.environ.get("PORT_KEY")
OS_API_KEY=os.environ.get("SEA_KEY")

def process_json(raw_data, address):
    holdings = pd.DataFrame(raw_data['nfts'])
    holdings = holdings[['contract_address']]

    blacklist = ['0x495f947276749ce646f68ac8c248420045cb7b5e',
    '0x3b3ee1931dc30c1957379fac9aba94d1c48a5405',
    '0xbad6186e92002e312078b5a1dafd5ddf63d3f731',
    '0x2a46f2ffd99e19a89476e2f62270e0a35bbf0756',
    '0xabb3738f04dc2ec20f4ae4462c3d069d02ae045b',
    '0xb932a70a57673d89f4acffbe830e8ed7f75fb9e0',
    '0xb6dae651468e9593e4581705a09c10a76ac1e0c8',
    '0x495f947276749ce646f68ac8c248420045cb7b5e',
    '0x60f80121c31a0d46b5279700f9df786054aa5ee5',
    '0x6a5ff3ceecae9ceb96e6ac6c76b82af8b39f0eb3',
    '0xd07dc4262bcdbf85190c01c996b4c06a461d2430']
    holdings = holdings.drop(holdings[(holdings['contract_address'].isin(blacklist))].index)

    holdings = holdings.groupby(['contract_address']).size().reset_index()
    holdings.rename({0: 'count'}, axis=1, inplace=True)

    holdings['30day_avg'] = 0
    holdings['image'] = ''
    holdings['name'] = ''
    holdings['slug'] = ''

    HEAD = {"X-API-KEY": OS_API_KEY, "Accept": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"}

    for index, row in holdings.iterrows():
        URL = 'https://api.opensea.io/api/v1/asset_contract/'+row['contract_address']
        r = requests.get(url = URL, headers = HEAD)
        data = r.json()
        holdings.loc[index, 'image'] = data['image_url']
        holdings.loc[index, 'name'] = data['name']
        try:
            holdings.loc[index, 'slug'] = data['collection']['slug']
        except:
            holdings.loc[index, 'slug'] = 0

    for index, row in holdings.iterrows():
        if row['slug']!=0:
            URL = 'https://api.opensea.io/api/v1/collection/'+row['slug']+'/stats'
            r = requests.get(url = URL, headers = HEAD)
            data = r.json()
            holdings.loc[index, '30day_avg'] = data['stats']['thirty_day_average_price']
        else:
            holdings.loc[index, '30day_avg'] = 0

    holdings['value']=holdings['count']*holdings['30day_avg']
    holdings['30day_avg'] = holdings['30day_avg'].round(2)
    holdings['value'] = holdings['value'].round(2)

    return holdings

def call_nftport(address):
    HEAD = {'Authorization': NFTPORT_API_KEY, 'Content-Type': 'application/json'}
    URL = 'https://api.nftport.xyz/v0/accounts/'+address.strip()+'?chain=ethereum'

    r = requests.get(url = URL, headers = HEAD)
    data = r.json()
    return data

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/index4.html')

@app.route('/appraisal')
def appraisal():
    address = request.args.get('address')

    data = call_nftport(address)

    if data['response'] == 'OK':
        success = 'True'
        print("Load Page")
        return render_template('pages/index5.html', results = {"success": success, "address": address})
    else:
        success = 'False'
        return render_template('pages/index5.html', results = {"success": success, "address": address})


@app.route('/data')
def data():
    address = request.args.get('address')
    address = address[:-4] #gets rid of line break that I'm not sure why I get
    raw_data = call_nftport(address)
    df = process_json(raw_data, address)
    total = df['value'].sum()
    total = round(total, 2)
    print('Total1:'+ str(total))

    URL = 'https://api.coinpaprika.com/v1/coins/eth-ethereum/ohlcv/today'
    r = requests.get(url = URL)
    eth_data = r.json()
    eth_price = eth_data[0]['open']
    total_usd = total * eth_price
    total_usd = round(total_usd, 2)
    print('Total2:'+ str(total_usd))

    success = 'True'
    print(df)
    jsonDf = df.to_json(orient='index')
    return {"success": success, "data": jsonDf, "count": len(df), "total_eth": total, "total_usd": total_usd}

    # if data['response'] == 'OK':
    #     df = process_json(data, address)
    #     success = 'True'
    #     return {"success": success, "data": df, "count": len(df)}
    # else:
    #     df = []
    #     success = 'False'
    #     return {"success": success, "data": df, "count": len(df)}

#TODO: hide opensea key in env


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
