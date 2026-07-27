# --------------------------------------------------------
# Restore multiple VMs from a PG.
# Greg Kurzawa
# --------------------------------------------------------

import json
import time
import argparse
import cohesity

from rich import print as rprint
from rich import reconfigure
reconfigure(highlight=False)



# ----------------------------------------------------------
# get a protection group's ID from the name
# ----------------------------------------------------------

def get_protection_group_id(n):

    urn = '/v2/data-protect/protection-groups?tenantIds=' + t + '&names=' + n
    r = cohesity.fetch_api_data( urn, args )
    pgId = r['protectionGroups'][0]['id']

    return pgId



# ----------------------------------------------------------
# get the details of the latest run of a PG
# ----------------------------------------------------------

def get_objectIds_of_last_successful_pg_run(pg):

    oIds = []

    urn = '/v2/data-protect/protection-groups/' + pg + '/runs?tenantIds=' + t + '&numRuns=1&localBackupRunStatus=Succeeded&includeObjectDetails=True'
    r = cohesity.fetch_api_data( urn, args )
    objects = r['runs'][0]['objects']

    for o in objects:
        oDetails = {}
        oDetails['id'] = o['object']['id']
        oDetails['name'] = o['object']['name']
        # oIds.append(o['object']['id'])
        oIds.append(oDetails)

    return oIds



# ----------------------------------------------------------
# get the details of the latest run of a PG
# ----------------------------------------------------------

def get_snapshotIds_of_objects(oIds):

    sIds = []

    for o in oIds:
       urn = '/v2/data-protect/objects/' + str(o['id']) + '/runs?tenantIds=' + t + '&includeTenants=True'
       r = cohesity.fetch_api_data( urn, args )
       sIds.append(r['protectionRuns'][0]['localSnapshotInfo']['snapshotInfo']['snapshotId'])
       o['snapshotId'] = r['protectionRuns'][0]['localSnapshotInfo']['snapshotInfo']['snapshotId'] 

    return sIds



# ----------------------------------------------------------
# restore the latest snapshotId of a Protection Group
# ----------------------------------------------------------

def recover_vms_to_vapp(pg, sIds):

    # body required for a recovery
    # I don't know which of the below items are required; some can probably be removed.

    b = {
        'name': 'scripted-VM-recovery',
        'snapshotEnvironment': 'kVMware',
        'vmwareParams': {
            'recoveryAction': 'RecoverVMs',
            'objects': [],
            'recoverVmParams': {
                'targetEnvironment': 'kVMware',
                'vmwareTargetParams': {
                  'powerOnVms': False,
                  'continueOnError': False,
                  'recoveryProcessType': 'InstantRecovery',
                  'recoveryTargetConfig': {
                      'recoverToNewSource': True,
                      'newSourceConfig': {
                          'sourceType': 'kvCloudDirector',
                          'vCloudDirectorParams': {
                              'datastores': [],
                              'networkConfig': {
                                  'detachNetwork': True,
                                  'newNetworkConfig': { 'mappings': [] }
                              },
                              'source': {
                                  'id': sourceId,
                                  'name': sourceName
                                  }, 
                              'storageProfile': {
                                  'vcdUuid': storage_profile_uuid,
                                  'name': storage_profile_name
                                  },
                              'vApp': {
                                  'id': vAppTargetId,
                                  'name': vAppTargetName
                                  },
                              'vdc': {
                                  'id': vdcId,
                                  'name': vdcName
                                  },
                          }
                      }
                  },
                  'renameRecoveredVmsParams': { 'prefix': 'scripted-restore-' }
                }
            }
          }
      }


    for s in sIds:
        b['vmwareParams']['objects'].append( { 'snapshotId': s } )

    # print('body to post:')
    # print (b)
    
    urn = '/v2/data-protect/recoveries'
    r = cohesity.post_api_data( urn, args, body=b, tenant=t )

    # print('status')
    # print(r.status_code)
    # print('text')
    # print(r.text)

    if ( r.status_code != 201 ):
        rprint('[#ff0000]failed to start recovery[/]')
        rprint('[#ff0000]' + r.text + '[/]')
        exit(0)

    return r.text



# ----------------------------------------------------------
# monitor a recovery Id
# ----------------------------------------------------------

def monitor_recovery_status(r):

    recovery_complete = False
    i = 0

    while ( not recovery_complete ):

        time.sleep(5)

        urn = '/v2/data-protect/recoveries?tenantIds=' + t + '&ids=' + r['id']
        rec = cohesity.fetch_api_data( urn, args, tenant=t )

        try: s = rec['recoveries'][0]['status']
        except: s = 'Accepted'

        match s:
            case 'Accepted':
                ss = '[#6699ff]' + s + '[/]'
            case 'Running':
                ss = '[#cc66ff]' + s + '[/]'
            case 'Succeeded':
                ss = '[#27F550]' + s + '[/]'
            case 'Failed':
                ss = '[#ff0000]' + s + '[/]'
            case _:
                ss = '[#d1d1e0]' + s + '[/]'

        rprint('recovery [#ffffff]' + r['name'] + '[/] ([#ffffff]' + r['id'] + '[/]) status: ' + ss + ' (' + str(i) + ')\t\t\t', end='', flush=True)

        if ( s in {'Succeeded', 'Canceled', 'Failed'} ):
            recovery_complete = True
            return s

        else:
            print('\r', end='', flush=True)
            i += 1




# ------------------------------------------------
# MAIN
# ------------------------------------------------

t = '001107078/'

# ------------------------------------------------
# argument parsing
# ------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--cluster", help="Cohesity Cluster [west|east]", required=True)
parser.parse_args()
args = parser.parse_args()

# WARNING: If any of the below changes in the Cohesity or the vmWare environment, this script will fail.

if ( args.cluster == 'west' ):
    sourceName = 'iaas.cachewest.internal.cms.gov'
    sourceId = 327
    pgName = 'IAAS-COHESITY-WEST'
    vdcName = 'IAAS-COHESITY-WEST'
    vdcId = 7797
    vAppTargetId = 15499
    vAppTargetName = 'Recovered'
    storage_profile_uuid = 'urn:vcloud:vdcstorageProfile:0031f070-870b-49e7-8ddb-cb5f5c6be14c'
    storage_profile_name = 'VCD-VM-PLACEMENT'

if ( args.cluster == 'east' ):
    sourceName = 'iaas.cacheeast.internal.cms.gov'
    sourceId = 1780
    pgName = 'IAAS-COHESITY-EAST'
    vdcName = 'IAAS-COHESITY-EAST'
    vdcId = 22082
    vAppTargetId = 37429
    vAppTargetName = 'Recovered'
    storage_profile_uuid = 'urn:vcloud:vdcstorageProfile:60ad8d57-e9e7-4bcb-82ef-5da9d3a82cde'
    storage_profile_name = 'VCD-VM-PLACEMENT'



# validate token
cohesity.validate_token(args)

# lookup Protection Group ID
rprint('Protection Group: [#ffffff]' + pgName + '[/] ID:', ':zzz:', end='', flush=True)
pg = get_protection_group_id(pgName)
print('\b', end='', flush=True)
rprint('[#ffffff]' + pg + '[/]', flush=True)

# lookup objects in Protection Group run
rprint('collecting objects from last successful run of PG [#ffffff]' + pgName + '[/]')
objectIds = get_objectIds_of_last_successful_pg_run(pg)

# lookup snapshotIds of Objects (VMs)
rprint('collecting snapshotIds from Objects')
snapshotIds = get_snapshotIds_of_objects(objectIds)
for o in objectIds:
    rprint('object:[#ffffff]' + o['name'] + '[/] id:[#ffffff]' + str(o['id']) + '[/] snapshotId: ', end='', flush=True)
    if 'snapshotId' in o:
        rprint(':white_check_mark:')
    else:
        rprint(':x:')

# start the recovery
print('starting recovery of PG objects')
rs = recover_vms_to_vapp(pg, snapshotIds)
rj = json.loads(rs)
# print(rj)
rprint('recovery started; Id [#ffffff]' + rj['id'] + '[/]')

# monitor status of recovery
s = monitor_recovery_status(rj)
print('\n')

exit(0)
