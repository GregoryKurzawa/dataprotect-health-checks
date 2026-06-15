# --------------------------------------------------------
# Poll a Cohesity REST API to capture and display data
# Greg Kurzawa; gregkurzawa@protonmail.com
# --------------------------------------------------------

import json
import time
import statics
import argparse
import cohesity

from rich import print as rprint
from rich import reconfigure
reconfigure(highlight=False)



# ------------------------------------------------
# check for "stuck" (Running) archival runs
# ------------------------------------------------

def check_stuck_archival_runs():

    print('\n\nProtectionGroup Archival Runs')

    # urn = '/v2/data-protect/protection-groups?includeTenants=True&isActive=True&isPaused=False'
    # r = cohesity.fetch_api_data( urn, args )

    # for pgr in r['protectionGroups']:

        # urn = '/v2/data-protect/protection-groups/' + pgr['id'] + '/runs?includeTenants=True&archivalRunStatus=Running'

        # r = cohesity.fetch_api_data( urn, args )

        # if len(r['runs']) == 0:
            # rprint(':white_check_mark: no running archival jobs for ProtectionGroup [#ffffff]' + pgr['name'] + '[/]')

        # else:
            # try: target = r['runs'][0]['archivalInfo']['archivalTargetResults'][0]['targetName']
            # except: target = "na"
            # try: status = r['runs'][0]['archivalInfo']['archivalTargetResults'][0]['status']
            # except: status = "na"
            # print(':yellow_circle:' + ' ' + r['runs'][0]['protectionGroupName'] + ' ' + target + ' ' + status)


    urn = urn = '/v2/data-protect/protection-groups?includeTenants=True&includeLastRunInfo=true&lastRunArchivalStatus=Running'
    r = cohesity.fetch_api_data( urn, args )

    if ( r['protectionGroups'] ):

        for pg in r['protectionGroups']:
            rprint(':yellow_circle: [#ffffff]' + pg['name'] + '[/] has running archivals')

    else:
        rprint(':white_check_mark: no ProtectionGroups have running archivals')



# ------------------------------------------------
# check connectivity to remote clusters
# ------------------------------------------------

def check_remote_cluster_connectivity():

    print('\nRemote Cluster Connectivity')

    urn = '/v2/remote-clusters'
    r = cohesity.fetch_api_data( urn, args )

    for rc in r['remoteClusters']:

        isReachable = rc['replicationParams']['allEndpointsReachable']
        if (isReachable): isReachableText = '[#27F550]Connected[/]'
        else: isReachableText = '[#27A3F5]Disconnect[/]'
        rprint(rc['clusterName'] + ': ' + isReachableText)



# ------------------------------------------------
# start a ProtectionGroup run
# c: cluster [ east | west ]
# pg: ProtectionGroup ID
# t: tenand ID
# ------------------------------------------------

def start_ProtectionGroup_run( c, t, pg ):

    # The Cohesity "svc_api" account needs to have the "Operator" role for this to work.

    # This is the WEST ProtectionGroup ID we want to run:
    # id: 941427762677808:1683589804795:183521 name:IAAS-COHESITY-WEST

    # This is the EAST ProtectionGroup ID we want to run:
    # id: 5439535469053792:1682956843825:246138 name: IAAS-COHESITY-EAST

    # Body required for a POST to start a Run.
    b = {
        'runType': 'kRegular',
        'targetsConfig': {
            'usePolicyDefaults': True
        }
    }

    # Start a new run.
    print('\nStarting Run of ProtectionGroup ' + pg)
    urn = '/v2/data-protect/protection-groups/' + pg + '/runs'
    pr = cohesity.post_api_data( urn, args, body=b, tenant=t )

    # try: print(pr)
    # except: print('no return')
    # try: print(pr.text)
    # except: print('no text')

    # The POST returns the ID of the ProtectionGroup.

    return pr



# ------------------------------------------------
# monitor a ProtectionGroup run
# c: cluster [ east | west ]
# pg: ProtectionGroup ID
# t: tenand ID
# ------------------------------------------------

def monitor_ProtectionGroup_run( c, t, pg ):

    # get the time in USECS -1h
    # ti = ( int(time.time()) - 3600 ) * 1000000 # -1h
    # ti = ( int(time.time()) - 1800 ) * 1000000 # -.5h
    ti = ( int(time.time()) - 300 ) * 1000000 # -5m

    print ( 'waiting for PG Run to start ', end='', flush=True )

    pg_run_complete = False
    while ( not pg_run_complete ):

        time.sleep(3)

        urn = '/v2/data-protect/protection-groups/' + pg + '/runs?startTimeUsecs=' + str(ti)
        r = cohesity.fetch_api_data( urn, args, tenant=t )

        try: runs = len(r['runs'])
        except: runs = 0

        if ( runs >= 1 ):

            for run in r['runs']:

                # Local_startStr = cohesity.usecs_to_string(run['localBackupInfo']['startTimeUsecs'])
                # Local_endStr = cohesity.usecs_to_string(run['localBackupInfo']['endTimeUsecs'])
                # Local_succ_obj = str(run['localBackupInfo']['successfulObjectsCount'])
                # Local_fail_obj = str(run['localBackupInfo']['failedObjectsCount'])

                # try: repl_target = run['replicationInfo']['replicationTargetResults'][0]['clusterName']
                # except: repl_target = 'na'
                # try: arch_target = run['archivalInfo']['archivalTargetResults'][0]['targetName']
                # except: arch_target = 'na'

                try: local_status = run['localBackupInfo']['status']
                except: local_status = 'Not Started'
                try: repl_status = run['replicationInfo']['replicationTargetResults'][0]['status']
                except: repl_status = 'Not Started'
                try: arch_status = run['archivalInfo']['archivalTargetResults'][0]['status']
                except: arch_status = 'Not Started'

                if ( local_status == 'Succeeded' ): lsc = '[#27F550]Succeeded[/]'
                elif ( local_status == 'Accepted' ): lsc = '[#6699ff]Accepted[/]'
                elif ( local_status == 'Running' ): lsc = '[#cc66ff]Running[/]'
                else: lsc = '[##8c8c8c]' + local_status + '[/]'

                if ( repl_status == 'Succeeded' ): rsc = '[#27F550]Succeeded[/]'
                elif ( repl_status == 'Accepted' ): rsc = '[#6699ff]Accepted[/]'
                elif ( repl_status == 'Running' ): rsc = '[#cc66ff]Running[/]'
                else: rsc = '[##8c8c8c]' + repl_status + '[/]'

                if ( arch_status == 'Succeeded' ): asc = '[#27F550]Succeeded[/]'
                elif ( arch_status == 'Accepted' ): asc = '[#6699ff]Accepted[/]'
                elif ( arch_status == 'Running' ): asc = '[#cc66ff]Running[/]'
                else: asc = '[##8c8c8c]' + arch_status + '[/]'

                # Clear the last four lines to stdout.
                # print('\033[A\033[K\033[A\033[K\033[A\033[K\033[A\033[K', end='', flush=True)

                print('\r', end='', flush=True)
                rprint('PG:[#ffffff]' + run['protectionGroupName'] + '[/] Local:' + lsc + ' Replication:' + rsc + ' Archival:' + asc + '\t\t\t', end='', flush=True)

                if ( local_status == "Succeeded" and repl_status == "Succeeded" and arch_status == "Succeeded" ):
                    pg_run_complete = True
                    

        else:

            print ( '.', end='', flush=True )



# ------------------------------------------------
# fetch actifio sources; do not display
# ------------------------------------------------

def get_actifio_sources():

    urn = '/v2/data-protect/sources/registrations?tenantIds=actifio/&includeTenants=true'
    r = cohesity.fetch_api_data(urn, args)
    return r



# ------------------------------------------------
# fetch and display actifio sources
# ------------------------------------------------

def show_actifio_sources():

    r = get_actifio_sources()

    # display the last refresh date for all the sources.

    for re in r['registrations']:

        last_refresh_str = cohesity.msecs_to_string(re['lastRefreshedTimeMsecs'])

        status_color = '[#27F550]'  # (default) green
        if ( re['authenticationStatus'] != 'Finished' ):
            status_color = '[#FF4747]'  # red

        rprint ('id:[#99ccff]' + str(re['id']) +
                '[/] source:[#99ccff]' + re['sourceInfo']['name'] +
                '[/] status:' + status_color + re['authenticationStatus'] +
                '[/] last refresh: [#99ccff]' + last_refresh_str)

    return r



# ------------------------------------------------
# refresh actifio sources
# ------------------------------------------------

def refresh_actifio_sources():

    print('\nRefreshing actifio sources')

    r = get_actifio_sources()

    for re in r['registrations']:

        urn = '/v2/data-protect/sources/' + str(re['id']) + '/refresh'
        rprint ('refreshing source id:[#99ccff]' + str(re['id']) + '[/]: ', end='', flush=True)
        post_return = cohesity.post_api_data(urn, args, tenant='actifio/')

        if ( post_return.status_code == 204 ):
            rprint ('[#27F550]done[/]')

        else:
            rprint ('[#FF4747]unexpected return[/]')



# ------------------------------------------------
# argument parsing
# ------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--cluster", help="Cohesity Cluster [west|east]", required=True)
parser.parse_args()
args = parser.parse_args()

if ( args.cluster == 'west' ):
    pg = '941427762677808:1683589804795:183521'

if ( args.cluster == 'east' ):
    pg = '5439535469053792:1682956843825:246138'



# ------------------------------------------------
# validate token
# ------------------------------------------------

cohesity.validate_token(args)



# ------------------------------------------------
# data collection and display
# ------------------------------------------------

# report on connectivity to remote clusters
check_remote_cluster_connectivity()

# uncomment the following to start and monitor a ProtectionGroup Run
start_ProtectionGroup_run( args.cluster, '001107078/', pg )
monitor_ProtectionGroup_run( args.cluster, '001107078/', pg )

# check for stuck ProtectionGroup Runs
check_stuck_archival_runs()

refresh_actifio_sources()
print('\nsleeping 3s before checking refreshed sources\n')
time.sleep(3)
show_actifio_sources()

print('\nCohesity Health Check complete\n')

exit(0)
