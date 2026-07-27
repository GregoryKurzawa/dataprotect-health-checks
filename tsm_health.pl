#!/usr/bin/perl

use Term::ANSIColor;



# ------------------------------------------------------
# customize these variables
# ------------------------------------------------------

my $DSMC = '/usr/bin/dsmadmc';
my $euaid = 'kdrq';
my $password = '';

my @sp_server = ( "TSM2",
       		  "TSM3",
	 	  "TSM4",
		  "TSM5",
	 	  "TSM2_S3",
	          "TSM3_S3",
	 	  "TSM4_S3",
	 	  "TSM5_S3" );

# FOR TESTING SPECIFIC INSTANCES
# my @sp_server = ( "TSM3", "TSM3_S3", "TSM2", "TSM2_S3" );




# ------------------------------------------------------
# these variables should remain static
# ------------------------------------------------------

my %sp_pairs =   ( 'TSM2' => 'DRAAS-TSM5',
		   'TSM3' => 'DRAAS-TSM4',
		   'TSM4' => 'DRAAS-TSM3',
		   'TSM5' => 'DRAAS-TSM2' );



# ------------------------------------------------------
# These are the queries/commands we'll be running:
# ------------------------------------------------------

my $q_status = "q status";

my $q_summary = "SELECT
successful,
entity,
activity,
varchar_format(start_time, 'YYYY-MM-DD HH24:MI'),
varchar_format(end_time, 'YYYY-MM-DD HH24:MI'),
schedule_name
FROM summary
WHERE (activity='BACKUP' or activity='ARCHIVE')
AND end_time >= current_timestamp - 1 hours";

my $q_actlog = "q actlog begint=-1 msg=0839";

my $validate_cloud_conn = "validate cloud connection=S3_DBB";



# ------------------------------------------------------
# Run the queries on each SP server.
# ------------------------------------------------------

foreach ( @sp_server ) {

    print colored ( "\n  ***** $_ *****\n", "magenta" );

    my $status_check_successful = 1;
    print colored ( "\n[$_]", "bold blue" );
    print ( " Checking Status" );

    my @SPOUT_STATUS = `$DSMC -se=$_ -id=$euaid -pa=$password -dataonly=y -tab "$q_status"`;
    # print @SPOUT_STATUS;
    # exit 0;

    if ( $SPOUT_STATUS[0] =~ /ANS\d{4}E|ANS1051I/i ) {
	    print colored ( "\nFAILED: @SPOUT_STATUS\n", "red" );
	    $status_check_successful = 0;
    }

    # ------------------------------------------------------
    # Only proceed with additional testing if the initial
    # status check was successful.
    # ------------------------------------------------------
    
    if ($status_check_successful == 1) {

	print ("\n");

	my @td = split ( /\t/, $SPOUT_STATUS[2] );
	print ( "Last Restart: ");
	print colored ( "$td[6]\n", "green" );
	print ( "Availability: ");
	if ( $td[19] =~ /Enabled/i ) { print colored ("$td[19]\n", "green"); }
	else { print colored ("$td[19]\n", "red"); }
	print ( "Central Scheduler: " );
	if ( $td[30] =~ /Active/i ) { print colored ("$td[30]\n", "green"); }
	else { print colored ("$td[30]\n", "red"); }


	# Check Summary table for BACKUP/ARCHIVE summaries.
	# Not needed on S3 instances.
	
	if ( not $_ =~ /S3$/ ) {
	
		$success_count = 0;
		$fail_count = 0;
		$success_color = "red";
		$fail_color = "red";
	        print colored ( "\n[$_]", "bold blue" );
	        print ( " Checking BACKUP/ARCHIVE Summaries\n" );
	        my @SPOUT_SUMMARY = `$DSMC -se=$_ -id=$euaid -pa=$password -dataonly=y -tab "$q_summary"`;
		foreach ( @SPOUT_SUMMARY ) {
			if ( /^YES/i ) { $success_count += 1; }
			elsif ( /^NO/i ) { $fail_count += 1; }
		}
		if ( $success_count >= 1 ) { $success_color = "green"; }
		if ( $fail_count == 0 ) { $fail_color = "green"; }
		print ( "Successful backup/archive in past hour: " );
		print colored ( "$success_count\n", $success_color );
		print ( "Failed backup/archive in past hour: " );
		print colored ( "$fail_count\n", $fail_color );
		# print @SPOUT_SUMMARY;
	
	}


	# Check ActivityLog for sessions.

        print colored ( "\n[$_]", "bold blue" );
        print ( " Checking ActivityLog\n" );
        my @SPOUT_ACTLOG = `$DSMC -se=$_ -id=$euaid -pa=$password -dataonly=y -tab "$q_actlog"`;
	print ( "Sessions started in last hour: " );
        print colored ( scalar(@SPOUT_ACTLOG), "green" );
	print "\n";


	# Validate S3 connection.
	
	print colored ( "\n[$_]", "bold blue" );
	print ( " Validating S3 connection\n" );
	my @S3_CONN = `$DSMC -se=$_ -id=$euaid -pa=$password -dataonly=y -tab "$validate_cloud_conn"`;
	if ( $S3_CONN[0] =~ /^ANR3557I/ ) {
	 	print colored ( $S3_CONN[0], "green" ); }
	else { print colored ( $S3_CONN[0], "red" ); }


	# Test cross-site (TSM2 <-> TSM5; TSM3 <-> TSM4) connectivity.
	# Not needed on S3 instances.
	
	if ( not $_ =~ /S3$/ ) {
	
	        my $cross_site_conn = $sp_pairs{$_} . ": q status";
	        print colored ( "\n[$_]", "bold blue" );
	        print ( " Checking cross-site connectivity to $sp_pairs{$_}\n" );
	        my @CROSS_SITE = `$DSMC -se=$_ -id=$euaid -pa=$password -dataonly=y -tab "$cross_site_conn"`;
		if ( $CROSS_SITE[-1] =~ /^ANR1697I/ ) {
			print colored ( $CROSS_SITE[-1], "green" ); }
		else { print colored ( @CROSS_SITE, "red" ); }

	}

    }

    print "\n";

}



