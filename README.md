Cohesity and TSM health checks

   cohesity.py:			a library required by cohesity_health_check.py
   cohesity_health_check.py:	the main Cohesity health check script
   tsm_health.pl		the main TSM health check script

I suggest creating a Python virtual environment for use with the Cohesity script.

   /dataprotect-health-checks$ python3 -m venv venv

The following Python modules are required for using the Cohesity check:

   requests
   rich

You can install the needed modules from within the virtual environment:

   /dataprotect-health-checks$ source ./venv/bin/activate
   (venv) /dataprotect-health-checks$ pip3 install requests
   (venv) /dataprotect-health-checks$ pip3 install rich

Passwords will have to be added to both scripts and updated when changes occur.
