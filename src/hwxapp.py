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
from ricxappframe.xapp_frame import RMRXapp, rmr

from ricxappframe.e2ap.asn1 import IndicationMsg, SubResponseMsg, SubRequestMsg, ControlRequestMsg, ActionDefinition, SubsequentAction, ARRAY, c_uint8



from .utils.constants import Constants
from .manager import *

from .handler import *
from mdclogpy import Logger

SIZE = 256
MRC_SEND = None
MRC_RCV = None
MRC_BUF_RCV = None


class HWXapp:

    def __init__(self):
        print("this is the __init__")
        fake_sdl = getenv("USE_FAKE_SDL", False)
        self._rmr_xapp = RMRXapp(self._default_handler,
                                 config_handler=self._handle_config_change,
                                 rmr_port=4560,
                                 post_init=self._post_init,
                                 rmr_wait_for_ready=True,
                                 use_fake_sdl=False)
    
    @staticmethod
    def _rmr_send_w_meid(rmr_xapp, payload, mtype, meid, retries=100):
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
        sbuf = rmr.rmr_alloc_msg(vctx=rmr_xapp._mrc, size=len(payload), payload=payload, gen_transaction_id=True,
                                 mtype=mtype, meid=meid)

        for _ in range(retries):
            sbuf = rmr.rmr_send_msg(rmr_xapp._mrc, sbuf)
            if sbuf.contents.state == 0:
                rmr_xapp.rmr_free(sbuf)
                return True

        rmr_xapp.rmr_free(sbuf)
        return False

    def _post_init(self, rmr_xapp):
        """
        Function that runs when xapp initialization is complete
        """
        print("this is the post init")
        rmr_xapp.logger.info("HWXapp.post_init :: post_init called")
        # self.sdl_alarm_mgr = SdlAlarmManager()
        sdl_mgr = SdlManager(rmr_xapp)
        #sdl_mgr.sdlGetGnbList()
        #a1_mgr = A1PolicyManager(rmr_xapp)
        #a1_mgr.startup()
        sub_mgr = SubscriptionManager(rmr_xapp)
        #enb_list = sub_mgr.get_enb_list()
        #for enb in enb_list:
        #    sub_mgr.send_subscription_request(enb)
        gnb_list = sub_mgr.get_gnb_list()
        print(gnb_list)
        #for gnb in gnb_list:
        #    sub_mgr.send_subscription_request(gnb)
        #metric_mgr = MetricManager(rmr_xapp)
        #metric_mgr.send_metric()

        msgbuf = self.dummy_control_request()

        self._rmr_send_w_meid(rmr_xapp,msgbuf,12040, bytes(gnb_list[0].inventory_name, 'ascii'))
        #rmr_xapp.rmr_send()

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

    def _handle_config_change(self, rmr_xapp, config):
        """
        Function that runs at start and on every configuration file change.
        """
        rmr_xapp.logger.info("HWXapp.handle_config_change:: config: {}".format(config))
        rmr_xapp.config = config  # No mutex required due to GIL

    def _default_handler(self, rmr_xapp, summary, sbuf):
        """
        Function that processes messages for which no handler is defined
        """
        rmr_xapp.logger.info("HWXapp.default_handler called for msg type = " +
                                   str(summary[rmr.RMR_MS_MSG_TYPE]))
        rmr_xapp.rmr_free(sbuf)

    def createHandlers(self):
        """
        Function that creates all the handlers for RMR Messages
        """
        HealthCheckHandler(self._rmr_xapp, Constants.RIC_HEALTH_CHECK_REQ)
        A1PolicyHandler(self._rmr_xapp, Constants.A1_POLICY_REQ)
        SubscriptionHandler(self._rmr_xapp,Constants.SUBSCRIPTION_REQ)

    def start(self, thread=False):
        """
        This is a convenience function that allows this xapp to run in Docker
        for "real" (no thread, real SDL), but also easily modified for unit testing
        (e.g., use_fake_sdl). The defaults for this function are for the Dockerized xapp.
        """
        self.createHandlers()
        self._rmr_xapp.run(thread)

    def stop(self):
        """
        can only be called if thread=True when started
        TODO: could we register a signal handler for Docker SIGTERM that calls this?
        """
        self._rmr_xapp.stop()

    