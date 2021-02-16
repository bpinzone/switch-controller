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


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--baud-rate', type=int, default=115200, help='Baud rate. Default: 115200.')
    parser.add_argument('-p', '--port', type=str, default='/dev/ttyACM0', help='Serial port. Default: /dev/ttyACM0.')

    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud_rate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None)
    print('Using {:s} at {:d} baud for comms.'.format(args.port, args.baud_rate))

    empty_message = generate_message({}, defaultdict(int), {})

    commands = ['stick', 'hold_a', 'hold_b', 'exit']

    non_terminal_commands = ['a', 'left', 'right']
    num_responses_to_read = 0

    # buttons: set of strings (representing buttons that are pushed down.)
    # axes: dict: string->real value
    # hats: set of strings. (representing buttons that are pushed down)
    # def generate_message(pressed_buttons: set, axes: defaultdict, hats: set):

    # Sleep to give the Arduino time to set up
    time.sleep(.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(.5)

    while True:

        pressed_buttons = set()
        axes = defaultdict(int)
        hats = set()

        # Each LINE happens in the same frame.
        user_input = input('cmd >> ')
        # print(user_input)

        user_input = user_input.strip()

        amper_split = user_input.split('&&')
        amper_split = [a.strip() for a in amper_split]

        listen_after_this_iter = not all([c in non_terminal_commands for c in amper_split])

        for section in amper_split:

            space_split = section.split(' ')

            if space_split[0] in commands:

                if space_split[0] == 'stick':

                    assert len(space_split) == 3

                    stick = space_split[1]
                    assert stick == 'r', 'FUCK other sticks'

                    direction = space_split[2]
                    assert direction in ['up', 'down', 'left', 'right', 'center']
                    axes = get_axes(direction)

                elif space_split[0] == 'hold_a':
                    # NOTE: special mapping for arduino
                    pressed_buttons.add('x')

                elif space_split[0] == 'hold_b':
                    # NOTE: special mapping for arduino
                    pressed_buttons.add('y')

                elif space_split[0] == 'exit':
                    return

            else:
                assert len(space_split) == 1
                if space_split[0] in hatmapping:
                    hats.add(space_split[0])
                else:
                    assert space_split[0] in buttonmapping
                    pressed_buttons.add(space_split[0])


        message = generate_message(pressed_buttons, axes, hats)

        ser.write(message)
        ser.flushOutput()
        num_responses_to_read += 1

        if listen_after_this_iter:
            # print(f'Listening to a response of length: {str(num_responses_to_read)}')
            listen_after_this_iter = False
            response = ser.read(num_responses_to_read)
            # print('Read the response')
            if response != (b'U' * num_responses_to_read):
                print(f'Bad response: {response}')
            num_responses_to_read = 0


if __name__ == '__main__':
    main()
