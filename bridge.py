#!/usr/bin/env python3


import argparse
from contextlib import contextmanager

import sdl2
import sdl2.ext
import struct
import binascii
import serial
import math
import time
from collections import defaultdict

first_message_written = False

# 0 or 1
buttonmapping = [
    'y', 'b', 'a', 'x', 'l', 'r', 'zl', 'zr',
    'select', 'start', 'lclick', 'rclick', 'home', 'capture'
]

# real values
# mind axis_deadzone.
axismapping = [ 'lx', 'ly', 'rx', 'ry' ]

# 0 or 1
# d-pad
hatmapping = [ 'up', 'right', 'down', 'left' ]

axis_deadzone = 30000
trigger_deadzone = 0

# fuck the left stick.
def get_axes(direction):
    axes = defaultdict(int)
    if direction == 'up':
        axes['rx'] = 0
        axes['ry'] = -(axis_deadzone + 100)
    elif direction == 'down':
        axes['rx'] = 0
        axes['ry'] = axis_deadzone + 100
    elif direction == 'left':
        axes['rx'] = -(axis_deadzone + 100)
        axes['ry'] = 0
    elif direction == 'right':
        axes['rx'] = axis_deadzone + 100
        axes['ry'] = 0
    else:
        assert direction == 'center'
        axes['rx'] = 0
        axes['ry'] = 0

    return axes

# magic
hatcodes = [8, 0, 2, 1, 4, 8, 3, 8, 6, 7, 8, 8, 5, 8, 8]


# buttons: set of strings (representing buttons that are pushed down.)
# axes: dict: string->real value
# hats: set of strings. (representing buttons that are pushed down)
def generate_message(pressed_buttons: set, axes: defaultdict, hats: set):
    assert all((p in buttonmapping for p in pressed_buttons))
    assert all((k in axismapping for k in axes.keys()))
    assert all((h in hatmapping for h in hats))

    buttons_encoded = sum([1 << buttonmapping.index(button_name) for button_name in pressed_buttons])
    hat_encoded = hatcodes[sum([1 << hatmapping.index(d_pad_str) for d_pad_str in hats])]

    rawaxis_encoded = [axes[axis] for axis in axismapping]
    axis_encoded = [((0 if abs(x) < axis_deadzone else x) >> 8) + 128 for x in rawaxis_encoded]
    rawbytes = struct.pack('>BHBBBB', hat_encoded, buttons_encoded, *axis_encoded)
    return binascii.hexlify(rawbytes) + b'\n'


def send_message(ser, message, sleep_seconds):

    # 120ms -> 34 seconds, 33 seconds
    # 80ms -> 425, 428 messages, 34 seconds, 35 seconds
    # 40ms -> 952, 992, 970 messages, 41 seconds, 38 seconds

    # global first_message_written


    ser.write(message)
    # if not first_message_written:
    #     first_message_written = True
    #     time.sleep(.5)
    #     return

    # ser.reset_output_buffer()
    # wait for the arduino to request another state.
    print('about to read')
    response = ser.read(1)
    print('just read')
    if response == b'U':
        # break
        pass
    elif response == b'X':
        print('Arduino reported buffer overrun or time utility does not work.')
    else:
        print(response)

    # ser.reset_input_buffer()
    # time.sleep(sleep_seconds)
    # print('WAT')


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--baud-rate', type=int, default=115200, help='Baud rate. Default: 115200.')
    parser.add_argument('-p', '--port', type=str, default='/dev/ttyACM0', help='Serial port. Default: /dev/ttyACM0.')

    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud_rate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None)
    print('Using {:s} at {:d} baud for comms.'.format(args.port, args.baud_rate))

    empty_message = generate_message({}, defaultdict(int), {})

    commands = ['stick', 'hold_a', 'hold_b', 'exit']

    # buttons: set of strings (representing buttons that are pushed down.)
    # axes: dict: string->real value
    # hats: set of strings. (representing buttons that are pushed down)
    # def generate_message(pressed_buttons: set, axes: defaultdict, hats: set):

    # Sleep to give the Arduino time to set up
    time.sleep(.5)

    while True:


        pressed_buttons = set()
        axes = defaultdict(int)
        hats = set()

        # Each LINE happens in the same frame.
        user_input = input('cmd >> ')
        print(user_input)

        user_input = user_input.strip()

        amper_split = user_input.split('&&')

        hold_time = 50 / 1000
        # print('hold time is:' + str(hold_time))

        for section in amper_split:

            section = section.strip()
            space_split = section.split(' ')

            if space_split[0] in commands:

                if space_split[0] == 'stick':

                    assert len(space_split) == 3

                    stick = space_split[1]
                    assert stick == 'r', 'FUCK other sticks'

                    direction = space_split[2]
                    hold_time = .15
                    assert direction in ['up', 'down', 'left', 'right', 'center']
                    axes = get_axes(direction)

                elif space_split[0] == 'hold_a':
                    hold_time = 1
                    # NOTE: special mapping for arduino
                    pressed_buttons.add('x')

                elif space_split[0] == 'hold_b':
                    hold_time = 1
                    # NOTE: special mapping for arduino
                    pressed_buttons.add('y')

                elif space_split[0] == 'exit':
                    send_message(ser, empty_message, 0.5)
                    return

            else:
                assert len(space_split) == 1
                if space_split[0] in hatmapping:
                    hats.add(space_split[0])
                else:
                    assert space_split[0] in buttonmapping
                    pressed_buttons.add(space_split[0])


        message = generate_message(pressed_buttons, axes, hats)

        send_message(ser, message, hold_time)
        # send_message(ser, empty_message, hold_time)


if __name__ == '__main__':
    main()
