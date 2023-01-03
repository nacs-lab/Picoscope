import ctypes
from picosdk.ps2000a import ps2000a as ps
from picosdk.functions import assert_pico_ok
import array
import math

def getPicoInfo(hdl, info_name, buf_len):
    c_buf_len = ctypes.c_int16(buf_len)
    buf = ctypes.create_string_buffer(buf_len)
    req_sz = ctypes.c_int16()
    status = ps.ps2000aGetUnitInfo(hdl, buf, c_buf_len, ctypes.byref(req_sz), ps.PICO_INFO[info_name])
    assert_pico_ok(status)
    # preallocated buffer size not large enough, so raise an error.
    if req_sz.value > buf_len:
        raise Exception("Buffer not big enough to hold serial number of PicoScope. Required sz: " + str(req_sz.value) + "Buf len: " + str(buf_len))
    return array.array('b', buf.raw).tobytes().decode().strip('\x00')

def getChn(chn_name):
    if chn_name.casefold() == "A".casefold():
        chn = ps.PS2000A_CHANNEL["PS2000A_CHANNEL_A"]
    elif chn_name.casefold() == "B".casefold():
        chn = ps.PS2000A_CHANNEL["PS2000A_CHANNEL_B"]
    elif chn_name.casefold() == "C".casefold():
        chn = ps.PS2000A_CHANNEL["PS2000A_CHANNEL_C"]
    elif chn_name.casefold() == "D".casefold():
        chn = ps.PS2000A_CHANNEL["PS2000A_CHANNEL_D"]
    else:
        raise Exception("Channel should be a,b,c or d")
    return chn

def getCoupling(couple_type):
    if couple_type.casefold() == "AC".casefold():
        couple_type = ps.PS2000A_COUPLING["PS2000A_AC"]
    elif couple_type.casefold() == "DC".casefold():
        couple_type = ps.PS2000A_COUPLING["PS2000A_DC"]
    else:
        raise Exception("Coupling type should be ac or dc")
    return couple_type

def getVRange(maxV):
    if maxV <= 20e-3:
        V_range = ps.PS2000A_RANGE["PS2000A_20MV"]
    elif maxV <= 50e-3:
        V_range = ps.PS2000A_RANGE["PS2000A_50MV"]
    elif maxV <= 100e-3:
        V_range = ps.PS2000A_RANGE["PS2000A_100MV"]
    elif maxV <= 200e-3:
        V_range = ps.PS2000A_RANGE["PS2000A_200MV"]
    elif maxV <= 500e-3:
        V_range = ps.PS2000A_RANGE["PS2000A_500MV"]
    elif maxV <= 1:
        V_range = ps.PS2000A_RANGE["PS2000A_1V"]
    elif maxV <= 2:
        V_range = ps.PS2000A_RANGE["PS2000A_2V"]
    elif maxV <= 5:
        V_range = ps.PS2000A_RANGE["PS2000A_5V"]
    elif maxV <= 10:
        V_range = ps.PS2000A_RANGE["PS2000A_10V"]
    elif maxV <= 20:
        V_range = ps.PS2000A_RANGE["PS2000A_20V"]
    else:
        raise Exception("Maximum voltage on PicoScope is 20V")
    return V_range

def VRangeToV(V_range):
    if V_range == ps.PS2000A_RANGE["PS2000A_20MV"]:
        return 20e-3
    elif V_range == ps.PS2000A_RANGE["PS2000A_50MV"]:
        return 50e-3
    elif V_range == ps.PS2000A_RANGE["PS2000A_100MV"]:
        return 100e-3
    elif V_range == ps.PS2000A_RANGE["PS2000A_200MV"]:
        return 200e-3
    elif V_range == ps.PS2000A_RANGE["PS2000A_500MV"]:
        return 500e-3
    elif V_range == ps.PS2000A_RANGE["PS2000A_1V"]:
        return 1
    elif V_range == ps.PS2000A_RANGE["PS2000A_2V"]:
        return 2
    elif V_range == ps.PS2000A_RANGE["PS2000A_5V"]:
        return 5
    elif V_range == ps.PS2000A_RANGE["PS2000A_10V"]:
        return 10
    elif V_range == ps.PS2000A_RANGE["PS2000A_20V"]:
        return 20
    else:
        raise Exception("Invalid V_range")

def getTriggerDirection(direction):
    if direction.casefold() == "ABOVE".casefold():
        return ps.PS2000A_THRESHOLD_DIRECTION["PS2000A_ABOVE"]
    elif direction.casefold() == "BELOW".casefold():
        return ps.PS2000A_THRESHOLD_DIRECTION["PS2000A_BELOW"]
    elif direction.casefold() == "RISING".casefold():
        return ps.PS2000A_THRESHOLD_DIRECTION["PS2000A_RISING"]
    elif direction.casefold() == "FALLING".casefold():
        return ps.PS2000A_THRESHOLD_DIRECTION["PS2000A_FALLING"]
    elif direction.casefold() == "RISING_OR_FALLING".casefold():
        return ps.PS2000A_THRESHOLD_DIRECTION["PS2000A_RISING_OR_FALLING"]
    else:
        raise Exception("Invalid Trigger direction")

def getSampleRate(model_num):
    # model_num is a string
    # returns a sampling rate in Samples/second
    if model_num == "2204A":
        return 100e6
    elif model_num == "2205A":
        return 200e6
    elif model_num == "2405A" or model_num == "2206B":
        return 500e6
    elif model_num == "2406B" or model_num == "2207B" or model_num == "2407B" or model_num == "2208B" or model_num == "2408B":
        return 1e9
    else:
        raise Exception("Model not supported")

def calcTimebase(model_num, dt):
    sample_rate = getSampleRate(model_num)
    if sample_rate == 500e6:
        if dt < 4e-9:
            timebase = 0
            interval_ns = 4e-9
        elif dt < 8e-9:
            timebase = 1
            interval_ns = 8e-9
        elif dt < 16e-9:
            timebase = 2
            interval_ns = 16e-9
        elif dt > 68.7:
            raise Exception("timing resolution is too large")
        else:
            timebase = math.floor(dt * 625e5 + 2)
            interval_ns = (timebase - 2) / (625e5)
    elif sample_rate == 1e9:
        if dt < 2e-9:
            timebase = 0
            interval_ns = 2e-9
        elif dt < 4e-9:
            timebase = 1
            interval_ns = 4e-9
        elif dt < 8e-9:
            timebase = 2
            interval_ns = 8e-9
        elif dt > 34.3:
            raise Exception("timing resolution is too large")
        else:
            timebase = math.floor(dt * 125e6 + 2)
            interval_ns = (timebase - 2) / (125e6)
    else:
        raise Exception("Automatic timebase calculation from sample rate needs implementation")
    return timebase, interval_ns

def makeChnDict(enabled, couple_type, V_range, offset, orig_name):
    chn_dict = dict()
    chn_dict["enabled"] = enabled
    chn_dict["V_range"] = V_range
    chn_dict["offset"] = offset
    chn_dict["orig_name"] = orig_name
    return chn_dict
