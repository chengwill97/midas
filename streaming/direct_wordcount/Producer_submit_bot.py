#!/usr/bin/env python

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__   = "MIT"

import sys
import os
import radical.pilot as rp
import numpy as np
import time

#os.environ['RADICAL_PILOT_DBURL']= 'mongodb://sean:1234@ds019678.mlab.com:19678/pilot_test'
#os.environ['RADICAL_PILOT_PROFILER']= 'TRUE'
os.environ['RADICAL_PILOT_VERBOSE']= 'DEBUG'

""" DESCRIPTION: Tutorial 1: A Simple Workload consisting of a Bag-of-Tasks
"""

# READ: The RADICAL-Pilot documentation: 
#   http://radicalpilot.readthedocs.org/en/latest
#
# Try running this example with RADICAL_PILOT_VERBOSE=debug set if 
# you want to see what happens behind the scences!


#------------------------------------------------------------------------------
#
def pilot_state_cb (pilot, state):

    if not pilot:
        return

    print "[Callback]: ComputePilot '%s' state: %s." % (pilot.uid, state)

    if state == rp.FAILED:
        sys.exit (1)


#------------------------------------------------------------------------------
#
def unit_state_cb (unit, state):

    if not unit:
        return

    global CNT

    print "[Callback]: unit %s on %s: %s." % (unit.uid, unit.pilot_id, state)

    if state == rp.FAILED:
        print "stderr: %s" % unit.stderr
        sys.exit(2)


#------------------------------------------------------------------------------
#
if __name__ == "__main__":


    session = rp.Session()
    print "session id: %s" % session.uid

    c = rp.Context('ssh')
#    c.user_id = "tg829618"
    session.add_context(c)
    # all other pilot code is now tried/excepted.  If an exception is caught, we
    # can rely on the session object to exist and be valid, and we can thus tear
    # the whole RP stack down via a 'session.close()' in the 'finally' clause.
    try:

        # Add a Pilot Manager. Pilot managers manage one or more ComputePilots.
        print "Initializing Pilot Manager ..."
        pmgr = rp.PilotManager(session=session)

        # Register our callback with the PilotManager. This callback will get
        # called every time any of the pilots managed by the PilotManager
        # change their state.
        pmgr.register_callback(pilot_state_cb)

        # ----- CHANGE THIS -- CHANGE THIS -- CHANGE THIS -- CHANGE THIS ------
        # 
        # Change the resource below if you want to run on a remote resource. 
        # You also might have to set the 'project' to your allocation ID if 
        # your remote resource does compute time accounting. 
        #
        # A list of preconfigured resources can be found at: 
        # http://radicalpilot.readthedocs.org/en/latest/machconf.html#preconfigured-resources
        # 
        pdesc = rp.ComputePilotDescription ()
    
        pdesc.resource = "xsede.comet_streaming"  # this is a "label", not a hostname
        pdesc.cores    = 70
        pdesc.runtime  = 5  # minutes
        pdesc.cleanup  = True  # clean pilot sandbox and database entries
        pdesc.project = "TG-MCB090174"
        #pdesc.queue = 'development'

        # submit the pilot.
        print "Submitting Compute Pilot to Pilot Manager ..."
        pilot = pmgr.submit_pilots(pdesc)

        # create a UnitManager which schedules ComputeUnits over pilots.
        print "Initializing Unit Manager ..."
        umgr = rp.UnitManager (session=session,
                               scheduler=rp.SCHED_DIRECT_SUBMISSION)

        # Register our callback with the UnitManager. This callback will get
        # called every time any of the units managed by the UnitManager
        # change their state.
        umgr.register_callback(unit_state_cb)

        # Add the created ComputePilot to the UnitManager.
        print "Registering Compute Pilot with Unit Manager ..."
        umgr.add_pilots(pilot)

        pilot_info = pilot.as_dict()
        
        #----------BEGIN USER DEFINED TEST-CU DESCRIPTION-------------------#
        cudesc = rp.ComputeUnitDescription()
        cudesc.executable = 'python'
        cudesc.arguments = ['test.py']
        cudesc.input_staging = ['test.py']
        cudesc.cores =1
        #-----------END USER DEFINED TEST-CU DESCRIPTION--------------------#
        cu_set = umgr.submit_units(cudesc)
        umgr.wait_units()
        print pilot_info

        NUMBER_JOBS  = 1 # the total number of cus to run
        NUMBER_PARTITIONS = 1
        TOPIC_NAME = 'KmeansList'
        pilot_info = pilot.as_dict()
        ZK_URL = pilot_info['resource_detail']['lm_detail']['zk_url']
        # create CU descriptions
        cudesc_list = []
 
        #----------BEGIN USER DEFINED KAFKA-CU DESCRIPTION-------------------#
        cudesc = rp.ComputeUnitDescription()
        cudesc.executable = 'kafka-topics.sh'
        cudesc.arguments = [' --create --zookeeper %s  --replication-factor 1 --partitions %d \
                                --topic %s' % (ZK_URL,NUMBER_PARTITIONS,TOPIC_NAME)]
        cudesc.cores =2
        #-----------END USER DEFINED KAFKA-CU DESCRIPTION--------------------#
        
        cu_set = umgr.submit_units(cudesc)
        
        umgr.wait_units()

        pilot_info = pilot.as_dict()
        zookeeper_url = pilot_info['resource_detail']['lm_detail']['zk_url']
        zk = zookeeper_url
        print pilot_info
        print pilot_info['resource_detail']['lm_detail']['brokers'][0]
        broker = pilot_info['resource_detail']['lm_detail']['brokers'][0] + ':9092'
        print broker
        #--------BEGIN USER DEFINED SPARK-CU DESCRIPTION-------#
        cudesc = rp.ComputeUnitDescription()
        cudesc.executable = "python"
        cudesc.arguments = ['producer.py  ',broker]
        cudesc.input_staging = ['producer.py'] 
        cudesc.cores = 2
        #---------END USER DEFINED CU DESCRIPTION---------------#
        
        cu_set = umgr.submit_units(cudesc)
#        umgr.wait_units()

        #------BEGIN USER DEFINED CONSUMER-CU DESCRIPTION-----#
       # cudesc = rp.ComputeUnitDescription()
       # cudesc.executable = "python"
       # cudesc.arguments = ['consumer.py ',broker]
       # cudesc.input_staging = ['consumer.py'] 
       # cudesc.cores = 2
        #---------END USER DEFINED CU DESCRIPTION---------------#


        #------BEGIN USER DEFINED CONSUMER-CU DESCRIPTION-----#
        cudesc = rp.ComputeUnitDescription()
        cudesc.executable = "kafka-console-consumer.sh"
        cudesc.arguments = [' --zookeeper %s --from-beginning --topic %s ' % (ZK_URL,TOPIC_NAME)]
        cudesc.cores = 2
        #---------END USER DEFINED CU DESCRIPTION---------------#

      #  cu_set2 = umgr.submit_units(cudesc)
      #  print 'Waiting for unit to complete'
      #  umgr.wait_units()

        #--conf spark.eventLog.enabled=true

        #--------BEGIN USER DEFINED SPARK-CU DESCRIPTION-------#
        cudesc = rp.ComputeUnitDescription()
        cudesc.pre_exec = ['mkdir /tmp/spark-events']
        cudesc.executable = "spark-submit"
        cudesc.arguments = ['--packages org.apache.spark:spark-streaming-kafka-0-8_2.11:2.0.2,\
          --conf spark.eventLog.enabled=true   direct_kafka_wordcount.py ',broker,TOPIC_NAME, '--verbose']
        cudesc.input_staging = ['direct_kafka_wordcount.py'] 
        cudesc.cores = 4
        #---------END USER DEFINED CU DESCRIPTION---------------#
        #cudesc_list.append(cudesc)

        # Submit the previously created ComputeUnit descriptions to the
        # PilotManager. This will trigger the selected scheduler to start
        # assigning ComputeUnits to the ComputePilots.
        print "Submit Compute Units to Unit Manager ..."
        cu_set = umgr.submit_units(cudesc)
        print "Waiting for spark"
        umgr.wait_units()
        print "All CUs completed:"

        print 'Timings'
        timers = pilot_info['resource_detail']['lm_detail']['startup_times']
        print timers
        spark = timers['spark']
        kafka = timers['zk_kafka']
        print 'kafka: '
        print kafka
        print 'spark'
        print spark


    

    except Exception as e:
        # Something unexpected happened in the pilot code above
        print "caught Exception: %s" % e
        raise

    except (KeyboardInterrupt, SystemExit) as e:
        # the callback called sys.exit(), and we can here catch the
        # corresponding KeyboardInterrupt exception for shutdown.  We also catch
        # SystemExit (which gets raised if the main threads exits for some other
        # reason).
        print "need to exit now: %s" % e

    finally:
        # always clean up the session, no matter if we caught an exception or
        # not.
         #print "Creating Profile"
        #ProfFile = open('{1}-{0}.csv'.format(cores,report_name),'w')
        #ProfFile.write('CU,Name,StageIn,Allocate,Exec,StageOut,Done\n')
        #for cu in cu_set:
            #extra one???
            #timing_str=[cu.uid,cu.name,'N/A','N/A','N/A','N/A','N/A','N/A']
            #for states in cu.state_history:
                #if states.as_dict()['state']=='AgentStagingInput':
                    #timing_str[3]= (states.as_dict()['timestamp']-pilot.start_time).__str__()
                #elif states.as_dict()['state']=='Allocating':
                    #timing_str[4]= (states.as_dict()['timestamp']-pilot.start_time).__str__()
                #elif states.as_dict()['state']=='Executing':
                    #timing_str[5]= (states.as_dict()['timestamp']-pilot.start_time).__str__()
                #elif states.as_dict()['state']=='AgentStagingOutput':
                    #timing_str[6]= (states.as_dict()['timestamp']-pilot.start_time).__str__()
                #elif states.as_dict()['state']=='Done':
                    #timing_str[7]= (states.as_dict()['timestamp']-pilot.start_time).__str__()

            #ProfFile.write(timing_str[0]+','+timing_str[1]+','+
             #              timing_str[2]+','+timing_str[3]+','+
              #             timing_str[4]+','+timing_str[5]+','+
               #            timing_str[6]+','+timing_str[7]+'\n')
       # ProfFile.close()

        print "closing session"
        session.close ()

        # the above is equivalent to
        #
        #   session.close (cleanup=True, terminate=True)
        #
        # it will thus both clean out the session's database record, and kill
        # all remaining pilots.




#-------------------------------------------------------------------------------
