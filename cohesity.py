import os
import sys
import time
import json
import requests
import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from rich import print as rprint
from rich import reconfigure
reconfigure(highlight=False)



# ------------------------------------------------
# test the age of the access token
# refresh if necessary
# fetch URN data from the Cohesity API
# ------------------------------------------------

def validate_token(args):

    TOKEN_MAX_AGE = 86400
    epoch_ti = int(time.time())

    try: m_ti = os.path.getmtime("token_cohesity_" + args.cluster)
    except:
        print ('token file does not exist')
        m_ti = 0

    if ( m_ti <= (epoch_ti - TOKEN_MAX_AGE) ):
        print ('cohesity token needs to be refreshed')
        refresh_token(args)
    else:
        print ('cohesity token is still good')



# --------------------------------------------------------------------------------
# Refresh the Cohesity token stored on disk.
# --------------------------------------------------------------------------------

def refresh_token(args):

    # If they passed in a 'dp_admin_pass' (args.dp_admin_pass) then use it, 
    # otherwise resort to the 'svc_api' account/password.
    # I don't like doing it this way.

    if ( 'dp_admin_pass' in args ):
        username = 'dp_admin'
        password = args.dp_admin_pass

    else:
        username = 'svc_api'
        password = ''

    ccFull = get_full_cluster_name(args.cluster)
    url = 'https://' + ccFull + '/irisservices/api/v1/public/accessTokens'

    h = {
        'Accept': 'application/json',
        'Content-type': 'application/json'
    }

    b = {
      "certificate": "string",      # needed?
      "domain": "LOCAL",
      "otpCode": "string",          # needed?
      "otpType": "Totp",            # needed?
      "password": password,
      "privateKey": "string",       # needed?
      "username": username
    }

    p = json.dumps(b)

    s = requests.Session()
    r = s.post(url, headers=h, data=p, verify=False).json()

    try: token = r['accessToken']

    except:
        print ('could not get token')
        print ('[' + r['errorCode'] + '] ' + r['message'])
        exit (0)

    token_file = 'token_cohesity_' + args.cluster
    with open(token_file, 'w') as file:
        file.write(token)



# --------------------------------------------------------------------------------
# Takes a Cohesity cluster's short name (cc) and returns a long name (ccFull)
# I did it this way so we only have to provide the shortname in the URL.
# --------------------------------------------------------------------------------

def get_full_cluster_name(cc):

    match cc:
        case 'x86dataprotecteast' | 'east':
            ccFull = 'x86dataprotecteast.storage.cacheeast.internal.cms.gov'
        case 'x86dataprotectwest' | 'west':
            ccFull = 'x86dataprotectwest.storage.cachewest.internal.cms.gov'
        case _:
            ccFull = 'failure'
 
    return ccFull



# --------------------------------------------------------------------------------
# Cohesity records timestamps in usecs (micro|milli -seconds (?)).
# This procedure converts usecs to a nicely formatted string.
# --------------------------------------------------------------------------------

def usecs_to_string(usecs):

    sex = (usecs/1000000)
    aTimeString = datetime.datetime.fromtimestamp(sex).strftime('%b %d, %Y @%H:%M')

    return aTimeString



# --------------------------------------------------------------------------------
# Same as "usecs_to_string" but works for msecs.
# --------------------------------------------------------------------------------

def msecs_to_string(msecs):

    sex = (msecs/1000)
    aTimeString = datetime.datetime.fromtimestamp(sex).strftime('%b %d, %Y @%H:%M')

    return aTimeString



# --------------------------------------------------------------------------------
# Fetch protection group Id from a protection group name.
# tenant Id also requried
# --------------------------------------------------------------------------------

def fetch_protection_group(args):

    urn = '/irisservices/api/v1/public/protectionJobs?tenantIds=' + args.tenant
    r = fetch_api_data(urn, args)

    for t in r:
        if ( t['name'] == args.protectionGroup ):
            return ( t['id'] )

    return False



# --------------------------------------------------------------------------------
# Fetch a VM array from a protectionGroup Id.
# The VM array SHOULD contain all the VMs that are included in the PG.
# It is built by inspecting data from the "includeLastRunAndStats" arg.
# --------------------------------------------------------------------------------

def fetch_vm_list(args, pgId):

    urn = '/irisservices/api/v1/public/protectionJobs?tenantIds=' + args.tenant + '&ids=' + str(pgId) + '&includeLastRunAndStats=true'
    r = fetch_api_data(urn, args)

    vms = []

    try:
        for l in r[0]['lastRun']['backupRun']['sourceBackupStatus']:
            # vms.append(l['source']['name'])
            a_vm = {} 
            a_vm['name'] = l['source']['name']
            a_vm['morItem'] = l['source']['vmWareProtectionSource']['id']['morItem']
            vms.append(a_vm)
    except: return (False)

    return (vms)



# --------------------------------------------------------------------------------
# Fetch a VM array containing vCenter Server IDs.
# --------------------------------------------------------------------------------

def fetch_vcs(args):

    urn = '/irisservices/api/v1/public/protectionSources?environments=kVMware&numLevels=2'
    r = fetch_api_data(urn, args)

    vcs = []

    for ps0 in r:

        if ( ps0['protectionSource']['vmWareProtectionSource']['type'] == 'kFolder' ) and ( ps0['protectionSource']['name'] != 'Datacenters' ):
            vc = {}
            vc['vCenterName'] = ps0['protectionSource']['name']
            vc['vCenterId'] = ps0['protectionSource']['id']
            vcs.append(vc)

        if ( 'nodes' in ps0 ):

            for ps1 in ps0['nodes']:

                if ( ps1['protectionSource']['vmWareProtectionSource']['type'] == 'kFolder' ) and ( ps1['protectionSource']['name'] != 'Datacenters' ):
                    vc = {}
                    vc['vCenterName'] = ps1['protectionSource']['name']
                    vc['vCenterId'] = ps1['protectionSource']['id']
                    vcs.append(vc)

    return(vcs)



# --------------------------------------------------------------------------------
# Fetch data from a Cohesity REST API URN.
# --------------------------------------------------------------------------------

def fetch_api_data(urn, args, **kwargs):

    cc = args.cluster					# the Cohesity Cluster
    ccFull = get_full_cluster_name(cc)			# the FQDN of the cluster

    # ------------------------------------------------
    # read token file from disk
    # ------------------------------------------------

    token_file = 'token_cohesity_' + cc
    with open(token_file, 'r') as file:
        token = file.readline().strip()

    h = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
    }

    if ( 'tenant' in kwargs ):
        h['X-IMPERSONATE-TENANT-ID'] = kwargs['tenant']

    url = 'https://' + ccFull + urn

    s = requests.Session()
    r = s.get(url, headers=h, verify=False).json()

    return r



# --------------------------------------------------------------------------------
# PUT data to Cohesity REST API URN.
# --------------------------------------------------------------------------------

def put_api_data(urn, args, **kwargs):

    cc = args.cluster                                   # the Cohesity Cluster
    ccFull = get_full_cluster_name(cc)                  # the FQDN of the cluster

    # ------------------------------------------------
    # read token file from disk
    # ------------------------------------------------

    token_file = 'token_cohesity_' + cc
    with open(token_file, 'r') as file:
        token = file.readline().strip()

    h = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
    }

    if ( 'tenant' in kwargs ):
        h['X-IMPERSONATE-TENANT-ID'] = kwargs['tenant']

    url = 'https://' + ccFull + urn

    s = requests.Session()

    b = json.dumps( kwargs['body'] ) 

    # rprint ('[#ff9966]bailing')
    r = s.put(url, headers=h, data=b, verify=False).json()
    return r



# --------------------------------------------------------------------------------
# POST data to Cohesity REST API URN.
# --------------------------------------------------------------------------------

def post_api_data(urn, args, **kwargs):

    cc = args.cluster                                   # the Cohesity Cluster
    ccFull = get_full_cluster_name(cc)                  # the FQDN of the cluster

    # ------------------------------------------------
    # read token file from disk
    # ------------------------------------------------

    token_file = 'token_cohesity_' + cc
    with open(token_file, 'r') as file:
        token = file.readline().strip()

    h = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
    }

    if ( 'tenant' in kwargs ):
        h['X-IMPERSONATE-TENANT-ID'] = kwargs['tenant']

    url = 'https://' + ccFull + urn

    # s = requests.Session()

    try: b = json.dumps( kwargs['body'] )
    except: b = ''

    # rprint ('[#ff9966]bailing')
    r = requests.post(url, headers=h, data=b, verify=False)
    return r
