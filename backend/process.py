import pandas as pd
import json
import math
import hashlib, binascii
import numpy as np
import time
from datetime import timedelta
from shutil import copyfile
from os import listdir
import re
from gcp import upload_blob, download_blob, upload_json
from io import StringIO
import plaid
import sys
sys.path.insert(1, '../private')
import keys as keys
import datetime

saveLocation = 'local'
def getFiles():
    dlFiles = listdir("./download")
    try:
        dlFiles.remove('.DS_Store')
    except:
        pass
    
    result = []
    for file in dlFiles:
        fileObject={"name":None, "data":None}
        newData = pd.read_csv("./download/"+file, header=None, names=newColumns)
        fileObject["name"] = file.split(".")[0]
        fileObject["data"] = newData
        result.append(fileObject)
    return result


def getFile(file):
    global saveLocation
    if (saveLocation=='local'):
        if file == "data":
            return pd.read_csv("./data/data.csv", header=None, names=oldColumns,index_col=False)
        elif file == "processed":
            return pd.read_csv("./data/processed.csv",index_col=False)
        elif file == "maps":
            return pd.read_csv("./data/1to1maps.csv", header=None, names=['item', 'subCategory'])
        elif file == "subCategories":
            return pd.read_csv("./data/categories.csv", header=None, names=['item', 'subCategory'])
        elif file == "categories":
            return pd.read_csv("./data/breakdown.csv", header=None, names=['subCategory', 'category'])
    if (saveLocation=='gcs'):
        if file == "data":
            download =  download_blob('data/data.csv')
            return pd.read_csv(download, header=None, names=oldColumns,index_col=False)
        elif file == "processed":
            download =  download_blob('data/processed.csv')
            return pd.read_csv(download,index_col=False)
        elif file == "maps":
            download =  download_blob('data/1to1maps.csv')
            return pd.read_csv(download, header=None, names=['item', 'subCategory'])
        elif file == "subCategories":
            download =  download_blob('data/categories.csv')
            return pd.read_csv(download, header=None, names=['item', 'subCategory'])
        elif file == "categories":
            download =  download_blob('data/breakdown.csv')
            return pd.read_csv(download, header=None, names=['subCategory', 'category'])

def writeFile(file, df):
    readableTime = datetime.datetime.now().strftime('%Y-%m-%d')

    global saveLocation
    if (saveLocation=='local'):
        if file =="maps":
            df.to_csv('./data/1to1maps.csv', index=False, header=False) 
            df.to_csv('./backup/1to1maps-'+readableTime+'.csv', index=False, header=False)  
        elif file=="subCategories":
            df.to_csv('./data/categories.csv', index=False, header=False) 
            df.to_csv('./backup/categories-'+readableTime+'.csv', index=False, header=False)   
        elif file =="data":
            df.to_csv('./data/data.csv', index=False, header=False)
            df.to_csv('./backup/data-'+readableTime+'.csv', index=False, header=False)    
    if (saveLocation=='gcs'):
        if file =="maps":
            upload_blob(df, 'data/1to1maps.csv')
            upload_blob(df, 'backup/1to1maps-'+readableTime+'.csv')
        elif file=="subCategories":
            upload_blob(df, 'data/categories.csv')
            upload_blob(df, 'backup/categories-'+readableTime+'.csv')
        elif file =="data":
            upload_blob(df, 'data/data.csv')
            upload_blob(df, 'backup/data-'+readableTime+'.csv')

def writeToJson(df):
    miliTime = int(round(time.time()))
    readableTime = datetime.datetime.now().strftime('%Y-%m-%d')

    items = convertToJsonArray(df)
    if (saveLocation == "local"):
        with open('../private/data.json', 'w') as jsonFile:
            json.dump(items, jsonFile)
    if (saveLocation == "gcs"):
        io = StringIO()
        json.dump(items, io)
        upload_json(io, 'data/data.json')
        upload_json(io, 'backup/data-'+readableTime+'.json')

# Hash Data

oldColumns=['date','item','debit','credit','subCategory','hash', 'account']
addedColumns = ['date','item','debit','credit','hash','account']
newColumns=['date','item','debit','credit','card']
processedColumns=['item','category','subCategory','date','year','month','debit','credit','balance', 'account']

def hashit(df):
    hashs = []
    for index, row in df.iterrows():
        h = hashlib.new('ripemd160')
        it = str(row['item'])
        it2= ' '.join(re.findall(r"[\w']+", it))
        h.update(it2.encode())
        h.update(str(row['credit']).encode())
        h.update(str(row['debit']).encode())
        h.update(str(row['date']).encode())
        hashed =h.hexdigest()
        hashs.append(hashed)
    return hashs

def testDf(df):
    assert df.dtypes['debit'] == 'float64'
    assert df.dtypes['credit'] == 'float64'

def fixDf(df):
    global oldColumns
    df['subCategory'].fillna("",inplace=True)
    df=df[oldColumns]
    return df

def saveDf(df, fileName, header):
    readableTime = datetime.datetime.now().strftime('%Y-%m-%d')

    global saveLocation
    if (saveLocation=="local"):
        df.to_csv('./backup/'+fileName+'-'+readableTime+'.csv', index=False, header=header)
        df.to_csv('./data/'+fileName+'.csv', index=False, header=header)  
    elif (saveLocation=="gcs"):
        # df.to_csv('./temp/'+fileName+'-'+str(miliTime)+'.csv', index=False, header=header)
        # df.to_csv('./temp/'+fileName+'.csv', index=False, header=header)  
        upload_blob(df, 'backup/'+fileName+'-'+readableTime+'.csv', header)
        upload_blob(df, 'data/'+fileName+'.csv', header)

def changeSubcategory(hash, subCategory):
    df = getFile("data")
    df['subCategory'].fillna("",inplace=True)
    df.fillna(value=0,inplace=True)
    df.loc[df["hash"] == hash, "subCategory"] = subCategory
    return df
    
def findNewItems(old, new, fileName):
    new['hash']= hashit(new)
    hashfound = []
    for index, row in new.iterrows():
        hashfound.append(row['hash'] in old['hash'].values)
    new['hashfound']=hashfound
    new.loc[new['hashfound'] == False, 'account'] = fileName;
    newItems = new[new['hashfound'] == False]
    return newItems

def convertToJsonArray(df):
    # columns = df.columns
    result = []
    for i, row in df.iterrows():
        dummy = {}
        for column in df.keys():
            dummy[column]=row[column]
        result.append(dummy)
    # result = df.to_dict('records')
    return(result)


def listNewItems(files):
    global oldColumns
    old = getFile('data')
    old['subCategory'].fillna("",inplace=True)
    old.fillna(value=0,inplace=True)
    testDf(old)

    combinedAll = old[oldColumns]
    combinedNew = pd.DataFrame(columns=oldColumns)

    for new in files:
        newData = new['data']
        newName = new['name']
        newData.fillna(value=0,inplace=True)
        testDf(newData)

        newItems = findNewItems(combinedAll, newData, newName)
        newToSave = newItems[addedColumns]

        print(newName+" - "+str(len(newToSave))+" new items found")

        combinedAll = pd.concat([combinedAll, newToSave])
        combinedNew = pd.concat([combinedNew, newToSave])
        
    combinedNew = fixDf(combinedNew)
    return combinedNew

# Process Hashed Data
def processData(newItems,doAll = False):
    if doAll:
        data = getFile('data')
    else:
        newItems.reset_index(inplace=True)
        data = newItems.copy()

    maps = getFile('maps')
    subCategories = getFile('subCategories')
    categories = getFile('categories')

    categoryMap ={}
    for i, row in categories.iterrows():
        categoryMap[row['subCategory']] = row['category']

    data.fillna("", inplace=True)

    subCatArray = []
    # first mapping the 1to1 mappings
    for i, row in data.iterrows():
        if (row['subCategory'] != ""):
            subCatArray.append(row['subCategory'])
        else:
            try:
                index = pd.Index(maps['item']).get_loc(row['item'].rstrip())
                subCategory = maps.loc[index]['subCategory']
                subCatArray.append(subCategory)
            except:
                subCatArray.append("")

    # then mapping all the general categories
    data['subCategory'] = subCatArray
    subCatArray = pd.Series(subCatArray) 

    for i, categoryRow in subCategories.iloc[::-1].iterrows():
        indo = ((data['item'].str.upper().str.contains(categoryRow['item'].upper())) & (data['subCategory']==""))
        subCatArray[indo] = categoryRow['subCategory']

    data['balance']=data['credit']-data['debit']

    # finally taking care of special categories with logic
    specialCategories = subCategories[subCategories['item'].str.contains('{{')]
    for i, categoryRow in specialCategories.iterrows():
        itemValuePair = categoryRow['item'].replace('}}', '').split('{{')
        indo = (data['item'].str.contains(itemValuePair[0].rstrip()) & (data['balance']==(float(itemValuePair[1]))))
        subCatArray[indo] = categoryRow['subCategory']

    data['subCategory'] = subCatArray
    data['category'] = data['subCategory'].map(categoryMap)
    data['year']= pd.to_datetime(data['date']).dt.year
    data['month']= pd.to_datetime(data['date']).dt.month 
    return data

def runProcess(files):
    newItems = listNewItems(files)
    if(newItems['item'].count() > 0):
        processedData = processData(newItems)   
        dataWithoutCategory = (processedData[processedData['subCategory'] == ""])
        if(len(dataWithoutCategory) == 0):
            processedAlready = getFile('processed')
            processedAll = pd.concat([processedData, processedAlready])
            processedToSave = processedAll[processedColumns].sort_values(by='date', ascending=False)
            saveDf(processedToSave, 'processed', True)

            dataAll = getFile('data')
            combinedData = pd.concat([dataAll, newItems])
            combinedData = combinedData[oldColumns]
            saveDf(combinedData, 'data', False)

            writeToJson(processedToSave)
            return({"missing": False,"items": processedData})
            print("SAVED")
        else:
            print('Found Gaps, NOT SAVED')
            # print(dataWithoutCategory[['item','date','balance']])
            itemsToReturn = dataWithoutCategory[['hash','item','date','balance', 'account']]
            return({"missing": True,"items": itemsToReturn})
    #       dataWithoutCategory[['item','date','balance']].to_csv('./processed/not_found.csv')
    else:
        print('no new items')
        return({"missing": False, "items": pd.DataFrame()})
        
def resetToCurrentData():
    processedData = processData(None, True)  
    processedToSave = processedData[processedColumns].sort_values(by='date', ascending=False)
    saveDf(processedToSave, 'processed', True)
    writeToJson(processedToSave)

# files = getFiles()
# runProcess(files)


def accountName(name, accountList):
    result = None
#     result = 'debit' if name=='1XxA8g36Dks69YKZVM3Yfbgpprwo7ECmVv9zw' else None
    if result == None:
        result= accountList[accountList['accountId']==name]['account'].values[0]
    if (result == "Visa Cad"):
        result = "visa"
    elif (result == 'Personal Line Of Credit'):
        result = "line"
    elif (result=="Eadvantage Savings Account"):
        result = "savings"
    elif (result=="Tfsa Tax Advantage Savings Account"):
        result= "TFSA"
    elif (result== "Personal Chequing Account USD"):
        result = "USD"
    elif (result=="CIBC Smart Account"):
        result = "debit"
        
    return result

# client = plaid.Client(client_id = keys.PLAID_CLIENT_ID, secret=keys.PLAID_SECRET,
#                       public_key=keys.PLAID_PUBLIC_KEY, environment=keys.PLAID_ENV, api_version='2019-05-29')


def getTransactions(start_date, end_date):
    
    response = client.Transactions.get(keys.access_token,
                                       start_date=start_date,
                                       end_date=end_date, count=500)
    print("# Transactions found" , response['total_transactions'])
    
    accountList= pd.DataFrame(columns=['account', 'subtype', 'type', 'balanceA', 'balanceC' , 'accountId'])
    for account in response['accounts']:
        name = account['name']
        subtype = account['subtype']
        type = account['type']
        balanceA= account['balances']['available']
        balanceC= account['balances']['current']
        accountId= account['account_id']

        b = pd.Series({'account':name,'subtype':subtype,'type':type, 'balanceA':balanceA, 'balanceC':balanceC, 'accountId':accountId})
        accountList = accountList.append(b, ignore_index=True )
        
        
    transactions = response['transactions']

    # Manipulate the count and offset parameters to paginate
    # transactions and retrieve all available data
    while len(transactions) < response['total_transactions']:
        response = client.Transactions.get(keys.access_token,
                                           start_date='2018-01-01',
                                           end_date='2019-02-01',
                                           offset=len(transactions)
                                          )
        transactions.extend(response['transactions'])
    tx= pd.DataFrame(columns=['date', 'item', 'debit','credit', 'card'])
    
    for account in transactions:
        name = account['name']
        date = account['date']
        debit = account['amount'] if account['amount'] >= 0 else 0;
        credit = -account['amount'] if account['amount'] < 0 else 0;        
        accountId= accountName(account['account_id'], accountList)

        b = pd.Series({'date':date,'item':name,'debit':debit, 'credit':credit, 'card':accountId})
        tx = tx.append(b, ignore_index=True )
    return tx

def parseDateBody(dateBody):
    print(dateBody)
    year = int(dateBody['year'])
    startdate = int(dateBody['startDate'])
    enddate = int(dateBody['endDate'])
    start = datetime.date(year, startdate, 1).strftime("%Y-%m-%d")
    end = datetime.date(year, enddate+1, 1) + timedelta(days = -1)
    end = end.strftime("%Y-%m-%d")
    return start,end

def alibaba():
    print('hello234')