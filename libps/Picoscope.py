import ctypes
from picosdk.ps2000a import ps2000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
import array
import libps.utils as utils
import numpy as np
import math

class Picoscope:
    def __init__(self, *args):
        # argument 1 is serial number if desired, if no argument, then just grabs the first PicoScope that is found
        if len(args) == 1:
            serial = args[0].encode()
        else:
            serial = None
        self.hdl = ctypes.c_int16()
        # opens the PicoScope
        status = ps.ps2000aOpenUnit(ctypes.byref(self.hdl), serial)
        assert_pico_ok(status)

        # input serial number
        if serial is not None:
            self.serial = serial
        else:
            # serial number was not known so grab from the PicoScope
            self.serial = utils.getPicoInfo(self.hdl, "PICO_BATCH_AND_SERIAL", 32)
        self.chnInfo = dict()
        self.model = utils.getPicoInfo(self.hdl, "PICO_VARIANT_INFO", 32)

    def __del__(self):
        # Destructor that closes the PicoScope
        status = ps.ps2000aStop(self.hdl)
        assert_pico_ok(status)
        print("Closing PicoScope " + str(self.serial))
        status = ps.ps2000aCloseUnit(self.hdl)
        assert_pico_ok(status)

    def setChn(self, chn_name, enabled, couple_type, maxV, offset):
        # Will try to convert from human readable inputs to the constants in the PicoScope
        # maxV will be the maximum (positive) voltage. A voltage range will be chosen to contain this max voltage.
        chn = utils.getChn(chn_name)
        couple_type = utils.getCoupling(couple_type)

        maxV = abs(maxV)
        V_range = utils.getVRange(maxV)

        status = ps.ps2000aSetChannel(self.hdl, chn, enabled, couple_type, V_range, offset)
        assert_pico_ok(status)
        self.chnInfo[chn] = utils.makeChnDict(enabled, couple_type, V_range, offset, chn_name)

    def disableChn(self, chn_name):
        # disables a certain channel, by setting enabled to 0. The other arguments are random, since I don't believe it should matter if the channel is getting disabled
        chn = utils.getChn(chn_name)
        status = ps.ps2000aSetChannel(self.hdl, chn, 0, ps.PS2000A_COUPLING["PS2000A_DC"], ps.PS2000A_RANGE["PS2000A_5V"], 0)
        assert_pico_ok(status)
        self.chnInfo[chn] = utils.makeChnDict(0, ps.PS2000A_COUPLING["PS2000A_DC"], ps.PS2000A_RANGE["PS2000A_5V"], 0)

    def setSimpleTrigger(self, chn_name, threshold, direction, delay, auto_trig):
        # threshold is in units of voltage
        # delay is in units of samples
        # auto_trig is in units of ms
        # direction is ABOVE, BELOW, RISING, FALLING, or RISING_OR_FALLING
        chn = utils.getChn(chn_name)
        # To determine threshold, we use both the current channel range and the max ADC counts
        maxADC = ctypes.c_int16()
        status = ps.ps2000aMaximumValue(self.hdl, ctypes.byref(maxADC))
        assert_pico_ok(status)
        if chn not in self.chnInfo:
            raise Exception("Channel not set before setting trigger")
        else:
            maxV = utils.VRangeToV(self.chnInfo[chn]["V_range"])
            if threshold >= maxV:
                raise Exception("Threshold larger than maximum possible value")
            elif threshold <= -maxV:
                raise Exception("Threshold smaller than minimum possible value")
            threshold = round(threshold / maxV * maxADC.value)
        direction = utils.getTriggerDirection(direction)
        status = ps.ps2000aSetSimpleTrigger(self.hdl, 1, chn, threshold, direction, delay, auto_trig)
        assert_pico_ok(status)

    def getSamplesToCapture(self, t_start, t_end, dt):
        # t_start is relative to the trigger, so should be negative
        # t_end is relative to the trigger, so should be positive
        # dt is the resolution
        # all are in units of seconds
        timebase, est_interval_s = utils.calcTimebase(self.model, dt)
        # get actual time interval from device
        act_interval_ns = ctypes.c_float()
        max_samples = ctypes.c_int32()
        est_preTriggerSamples = math.ceil(abs(t_start) / est_interval_s)
        est_postTriggerSamples = math.ceil(t_end / est_interval_s)
        status = ps.ps2000aGetTimebase2(self.hdl, timebase, est_preTriggerSamples + est_postTriggerSamples, ctypes.byref(act_interval_ns), 0, ctypes.byref(max_samples), 0)
        act_preTriggerSamples = math.ceil(abs(t_start / 1e-9) / act_interval_ns.value)
        act_postTriggerSamples = math.ceil((t_end / 1e-9) / act_interval_ns.value)
        return act_preTriggerSamples, act_postTriggerSamples, timebase, act_interval_ns.value

    def acquireBlock(self, preTriggerSamples, postTriggerSamples, timebase, act_interval_ns):
        # assumes all settings are set and we just need to acquire
        status = ps.ps2000aRunBlock(self.hdl, preTriggerSamples, postTriggerSamples, timebase, 0, None, 0, None, None)
        assert_pico_ok(status)
        # wait for acquisition
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            status = ps.ps2000aIsReady(self.hdl, ctypes.byref(ready))

        # set up data buffer locations for all enabled channels
        totalSamples = preTriggerSamples + postTriggerSamples
        buffers = dict()
        for key in self.chnInfo:
            is_enabled = self.chnInfo[key]["enabled"]
            if is_enabled:
                entry_key = self.chnInfo[key]["orig_name"]
                buffers[entry_key] = dict()
                this_bufferMax = (ctypes.c_int16 * totalSamples)()
                this_bufferMin = (ctypes.c_int16 * totalSamples)()
                status = ps.ps2000aSetDataBuffers(self.hdl, key, ctypes.byref(this_bufferMax), ctypes.byref(this_bufferMin), totalSamples, 0, 0)
                assert_pico_ok(status)
                buffers[entry_key]["Max"] = this_bufferMax
                buffers[entry_key]["Min"] = this_bufferMin
                buffers[entry_key]["V_range"] = self.chnInfo[key]["V_range"]
        # determines if any channels have any overvoltage, not currently used
        overflow = ctypes.c_int16()
        cTotalSamples = ctypes.c_int32(totalSamples)
        status = ps.ps2000aGetValues(self.hdl, 0, ctypes.byref(cTotalSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(status)

        # get Max voltage value
        maxADC = ctypes.c_int16()
        status = ps.ps2000aMaximumValue(self.hdl, ctypes.byref(maxADC))
        assert_pico_ok(status)

        # get the data
        data = dict()
        data["time"] = np.linspace(0, ((cTotalSamples.value) - 1) * act_interval_ns * 1e-9, cTotalSamples.value).tolist()
        for key in buffers:
            data[key] =(np.array(adc2mV(buffers[key]["Max"], buffers[key]["V_range"], maxADC)) / 1e3).tolist()
        return data
