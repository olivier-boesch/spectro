#!/bin/env python
# -*- coding: utf8 -*-
# #########################################################################
# Spectro v0.5
#   Olivier Boesch (c) 2019
#   Secomam s250 and Prim Spectrometers driver File - asynchronous version
# #########################################################################

# Backend Code ####################################
import struct
import serial

__author__ = "Olivier Boesch"
__version__ = "0.5 - 02/2019"

# Commands
Cmd_Prefix = b'\x1B'
Cmd_Init = b'\x5A'
Ans_Init_Ok = b'\x4F'
Ans_Init_Nok = b'\x4E'
Cmd_Firmware = b'\x22'
Cmd_Autotest = b'\x33'
Ans_Autotest_Ok = b'\x00'
Cmd_SetWavelength = b'\x31'
Ans_SetWavelength_Ok = b'\x1B'
Cmd_GetZeroAbs = b'\x30'
Ans_GetZeroAbs_Ok = b'\x54'
Cmd_GetAbs = b'\x32'
Ans_GetAbs_Ok = b'\x54'
Cmd_GetAbsData = b'\x45'
Cmd_BaseLine = b'\x34'
Ans_Baseline_Ok = b'\x1B'
Cmd_GetSpectrum = b'\x35'
Cmd_GetSpectrumData = b'\x00'  # fake command to get spectrum data ! not sent to device.
Cmd_GetType = b'\x51'
Cmd_Stop = b'\xE7'

# Spectrometer types
Secoman_Models = {b'T\x00': 'S250 I+/E+', b'T\x01': 'S250 T+', b'P\x02': 'Prim Advanced', b'P\x01': 'Prim Lignt'}


class S250Prim:
    waveLengthLimits = {'start': 330, 'end': 900, 'step': 3, 'speed': [1, 2, 3, 4, 5, 6, 7, 8]}
    serialComParameters = {'baudrate': 4800, 'bytesize': serial.EIGHTBITS, 'parity': serial.PARITY_NONE,
                           'stopbits': serial.STOPBITS_ONE}
    device_capabilities = {'serialcomparameters': serialComParameters, 'device': waveLengthLimits}
    connected = False
    zero_data = 0.
    spectrum_data = None
    spectrum_data_idx = None
    conn = None

    def __init__(self):
        pass

    def send(self, s):
        if self.connected:
            n = self.conn.write(s)
            return n

    def receive(self, n):
        if self.connected:
            c = self.conn.read(n)
            return c

    def return_command(self, data, cmd_sent):
        if cmd_sent == Cmd_Init:
            if data == Ans_Init_Ok:
                return True
            elif data == Ans_Init_Nok:
                return False
            return None
        elif cmd_sent == Cmd_Firmware:
            s = struct.unpack(">xB", data)[0]
            return s
        elif cmd_sent == Cmd_Autotest:
            return data == Ans_Autotest_Ok,int.from_bytes(data,'big')
        elif cmd_sent == Cmd_SetWavelength:
            return data == Ans_SetWavelength_Ok
        elif cmd_sent == Cmd_GetZeroAbs:
            return data == Ans_GetZeroAbs_Ok
        elif cmd_sent == Cmd_GetAbs:
            return data == Ans_GetAbs_Ok
        elif cmd_sent == Cmd_GetAbsData:
            data = struct.unpack(">Bh", data)
            val = data[1] / 10000.0
            return data[0], val
        elif cmd_sent == Cmd_BaseLine:
            return data == Ans_Baseline_Ok
        elif cmd_sent == Cmd_GetSpectrum:
            wlStart, N = struct.unpack(">xxHHx", data)
            self.spectrum_data = (wlStart, N)
            self.spectrum_data_idx = 0
            return wlStart, N
        elif cmd_sent == Cmd_GetSpectrumData:
            wlStart, N = self.spectrum_data
            i = self.spectrum_data_idx
            wlcurrent = wlStart + i
            i += 1
            self.spectrum_data_idx = i
            abs_val = struct.unpack(">h", data)[0] / 10000.
            return (wlcurrent, abs_val), i, N
        elif cmd_sent == Cmd_GetType:
            data = struct.unpack("2s", data)
            rawmodel = data[0]
            stringmodel = "Secomam " + Secoman_Models[rawmodel]
            return stringmodel, rawmodel
        else:
            return None

    def connect(self, port):
        try:
            self.conn = serial.Serial(port, baudrate=self.serialComParameters['baudrate'],
                                      parity=self.serialComParameters['parity'],
                                      stopbits=self.serialComParameters['stopbits'])
            self.connected = True
            return True
        except:
            self.connected = False
            return False

    def disconnect(self):
        try:
            self.conn.close()
        except:
            pass
        del self.conn
        self.conn = None
        self.connected = False

    def start_device(self):
        """ start_device : start spectrometer and test if initialization of spectrometer is completed - no arguments"""
        self.conn.flush()
        self.send(Cmd_Init)
        return Cmd_Init, 1

    def stop_device(self):
        """stop_device : stop spectrometer - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_Stop)
        return Cmd_Stop, 0

    def is_device_ready(self):
        """ is_device_ready : test if device is up and ready - no arguments"""
        self.conn.flush()
        self.send(Cmd_Init)
        return Cmd_Init, 1

    def get_firmware_version(self):
        """ get_firmware_version : get and return Prom version - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_Firmware)
        return Cmd_Firmware, 2

    def get_model_name(self):
        """ get_model_name : return complete model name - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_GetType)
        return Cmd_GetType, 2

    def perform_autotest(self):
        """ perform_autotest : performs AutoTest of spectrometer - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_Autotest)
        return Cmd_Autotest, 1

    def set_abs_wavelength(self, wl, gain=255):
        """ set_abs_wavelength : Set value of wavelength - [wl in nm] [gain from 0 to 255]"""
        self.conn.flush()
        data = struct.pack(">HxxB", wl, gain)
        self.send(Cmd_Prefix + Cmd_SetWavelength + data)
        return Cmd_SetWavelength, 1

    def get_abs_zero(self):
        """ get_abs_zero : get value of absorbance zero - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_GetZeroAbs)
        return Cmd_GetZeroAbs, 1

    def get_abs(self):
        """ get_abs : get value of absorbance - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_GetAbs)
        return Cmd_GetAbs, 1

    def get_abs_data(self):
        self.conn.flush()
        self.send(Cmd_GetAbsData)
        return Cmd_GetAbsData, 3

    def make_spectrum_baseline(self, wllo, wlhi, speed=8, res=3):
        """ make_spectrum_baseline : performs baseline of spectrum
                                     [wlLo in nm] [wlHi in nm] [speed from 1 to 8] [res = 3]"""
        data = struct.pack(">HHBBxx", wllo, wlhi, res, speed)
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_BaseLine + data)
        return Cmd_BaseLine, 1

    def get_spectrum_header(self):
        """ get_spectrum_header : Gets and returns spectrum header - no arguments"""
        self.conn.flush()
        self.send(Cmd_Prefix + Cmd_GetSpectrum)
        return Cmd_GetSpectrum, 7

    def get_spectrum_data(self):
        return Cmd_GetSpectrumData, 2
