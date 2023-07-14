# ==================================================================================
#
#       Copyright (c) 2020 Samsung Electronics Co., Ltd. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ==================================================================================

from os import getenv
from ricxappframe.xapp_frame import rmr, Xapp

from ricxappframe.e2ap.asn1 import IndicationMsg, SubRequestMsg, ControlRequestMsg, ActionDefinition, SubsequentAction
from ricxappframe.entities.rnib.nb_identity_pb2 import NbIdentity

from  ran_messages_pb2 import *

from time import sleep

class e2apXapp:

    SUB_REQ_RMR_ID          = 12010
    RIC_IND_RMR_ID          = 12050
    RIC_CONTROL_REQ_RMR_ID  = 12040

    def __init__(self):
        fake_sdl = getenv("USE_FAKE_SDL", False)
        self.engine = Xapp(rmr_port=4560,
                          rmr_wait_for_ready=True,
                          use_fake_sdl=False,
                          entrypoint=self.logic)

    def _get_gnb_list(self):
        return self.engine.get_list_gnb_ids()
    
    def get_gnb_id_list(self):
        """
        Returns a list containing the gnb ids as ascii strings. Each gnb id can be safely consumed by sender functions
        """
        gnbids = list()
        for gnb in self._get_gnb_list():
            print(gnb)
            gnbids.append(gnb.inventory_name)
        return gnbids
    
    def _rmr_send_w_meid(self, payload, mtype, meid, retries=100):
        """
        Allocates a buffer, sets payload and mtype, and sends

        Parameters
        ----------
        payload: bytes
            payload to set
        mtype: int
            message type
        retries: int (optional)
            Number of times to retry at the application level before excepting RMRFailure

        Returns
        -------
        bool
            whether or not the send worked after retries attempts
        """
        sbuf = rmr.rmr_alloc_msg(vctx=self.engine._mrc, size=len(payload), payload=payload, gen_transaction_id=True,
                                 mtype=mtype, meid=meid)

        for _ in range(retries):
            sbuf = rmr.rmr_send_msg(self.engine._mrc, sbuf)
            if sbuf.contents.state == 0:
                self.engine.rmr_free(sbuf)
                return True

        self.engine.rmr_free(sbuf)
        return False

    def logic(self):
        """
        Function that runs when xapp initialization is complete
        """
        return # I don't want to execute the following code
    
        # self.sdl_alarm_mgr = SdlAlarmManager()
 #       sdl_mgr = SdlManager(rmr_xapp)
        #sdl_mgr.sdlGetGnbList()
        #a1_mgr = A1PolicyManager(rmr_xapp)
        #a1_mgr.startup()
#        sub_mgr = SubscriptionManager(rmr_xapp)
        #enb_list = sub_mgr.get_enb_list()
        #for enb in enb_list:
        #    sub_mgr.send_subscription_request(enb)
        #gnb_list = sub_mgr.get_gnb_list()
        gnb_list = self.get_gnb_list() #self._rmr_xapp.get_list_gnb_ids()
        print(gnb_list)
        #for gnb in gnb_list:
        #    sub_mgr.send_subscription_request(gnb)
        #metric_mgr = MetricManager(rmr_xapp)
        #metric_mgr.send_metric()

        #msgbuf = self.dummy_control_request()
        #msgbuf = self.e2ap_control_request(self.e2sm_dummy_control_buffer())
        msgbuf = self.send_e2ap_sub_request(self.e2sm_dummy_control_buffer())
        self._rmr_send_w_meid(self,msgbuf,12040, bytes(gnb_list[0].inventory_name, 'ascii'))
        print("Waiting 5 seconds before starting printing messages")
        sleep(5)
        while True:
            for (summary,sbuf) in rmr_xapp.rmr_get_messages():
                print("_____________")
                #print(summary)

                indm = IndicationMsg()
                indm.decode(summary["payload"])

                resp = RAN_indication_response()
                resp.ParseFromString(indm.indication_message)
                print(resp)
                rmr.rmr_free_msg(sbuf)
                print("_____________")
            sleep(2)
        #rmr_xapp.rmr_send()
    
    def get_queued_rx_message(self):
        queued_msg = list()
        for (summary,sbuf) in self.engine.rmr_get_messages():
            queued_msg.append(summary)
            rmr.rmr_free_msg(sbuf)
        return queued_msg

    @staticmethod
    def e2sm_dummy_control_buffer():
        print("encoding initial ric indication request")
        master_mess = RAN_message()
        master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
        inner_mess = RAN_indication_request()
        inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
        #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
        master_mess.ran_indication_request.CopyFrom(inner_mess)
        buf = master_mess.SerializeToString()
        return buf
    
    @staticmethod
    def e2ap_control_request(payload):
        action_definitions = list()

        action_definition = ActionDefinition()
        action_definition.action_definition = payload
        action_definition.size = len(action_definition.action_definition)

        action_definitions.append(action_definition)

        subsequent_actions = list()

        subsequent_action = SubsequentAction()
        subsequent_action.is_valid = 1
        subsequent_action.subsequent_action_type = 1
        subsequent_action.time_to_wait = 1

        subsequent_actions.append(subsequent_action)
        control_request = ControlRequestMsg()
        try:
            [lencc, bytescc] = control_request.encode(24, 1, 0, bytes([1]), bytes([1]), payload, 0)
        except BaseException:
            assert False
        print("control request encoded {} bytes".format(lencc))
        return bytescc

    def send_e2ap_control_request(self,payload, gnb_id):
        e2ap_buffer = self.e2ap_control_request(payload)
        self._rmr_send_w_meid(e2ap_buffer,self.RIC_CONTROL_REQ_RMR_ID, bytes(gnb_id, 'ascii'))
        pass

    def send_e2ap_sub_request(self,payload, gnb_id):

        """
        Send an E2AP Subscription request 
        
        Parameters
        ----------
        payload: bytes
            E2SM payload injected into event trigger definition
        gnb_id: string
            ASCII string containing the recepient gNB id
        """

        action_definitions = list()

        action_definition = ActionDefinition()
        action_definition.action_definition = bytes([1])
        action_definition.size = len(action_definition.action_definition)

        # action_definitions.append(action_definition)

        subsequent_actions = list()

        subsequent_action = SubsequentAction()
        subsequent_action.is_valid = 1
        subsequent_action.subsequent_action_type = 1
        subsequent_action.time_to_wait = 1
        # subsequent_actions.append(subsequent_action)

        sub_request = SubRequestMsg()
        try:
            [_, bytescc] = sub_request.encode(24, 1, 0, payload, [1], [1],
                            action_definitions, subsequent_actions)
        except BaseException:
            assert False
        self._rmr_send_w_meid(bytescc,self.SUB_REQ_RMR_ID, bytes(gnb_id, 'ascii'))

    def dummy_control_request():
        action_definitions = list()

        action_definition = ActionDefinition()
        action_definition.action_definition = bytes([1])
        action_definition.size = len(action_definition.action_definition)

        action_definitions.append(action_definition)

        subsequent_actions = list()

        subsequent_action = SubsequentAction()
        subsequent_action.is_valid = 1
        subsequent_action.subsequent_action_type = 1
        subsequent_action.time_to_wait = 1

        subsequent_actions.append(subsequent_action)
        control_request = ControlRequestMsg()
        try:
            [lencc, bytescc] = control_request.encode(1, 1, 1, bytes([1]), bytes([1]), bytes([1]), 1)
        except BaseException:
            assert False
        print("control request encoded {} bytes".format(lencc))
        return bytescc

    def start(self, thread=False):
        """
        This is a convenience function that allows this xapp to run in Docker
        for "real" (no thread, real SDL), but also easily modified for unit testing
        (e.g., use_fake_sdl). The defaults for this function are for the Dockerized xapp.
        """
        #self.createHandlers()
        #self._rmr_xapp.run(thread)
        self.engine.run()

    def stop(self):
        """
        can only be called if thread=True when started
        TODO: could we register a signal handler for Docker SIGTERM that calls this?
        """
        self.engine.stop()

    