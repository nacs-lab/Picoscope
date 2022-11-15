import ctypes
from picosdk.ps2000a import ps2000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
import array

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
            buf_len = 32
            c_buf_len = ctypes.c_int16(buf_len)
            buf = ctypes.create_string_buffer(buf_len)
            req_sz = ctypes.c_int16()
            status = ps.ps2000aGetUnitInfo(self.hdl, buf, c_buf_len, ctypes.byref(req_sz), ps.PICO_INFO["PICO_BATCH_AND_SERIAL"])
            assert_pico_ok(status)
            # preallocated buffer size not large enough, so raise an error.
            if req_sz.value > buf_len:
                raise Exception("Buffer not big enough to hold serial number of PicoScope. Required sz: " + str(req_sz.value) + "Buf len: " + str(buf_len))
            self.serial = array.array('b', buf.raw).tobytes().decode()
    def __del__(self):
        print("Closing PicoScope " + self.serial)
        status = ps.ps2000aCloseUnit(self.hdl)
        assert_pico_ok(status)
