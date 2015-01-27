#! /usr/bin/env python
# Copyright (C) 2015  Arthur Yidi
# License: BSD Simplified

import os
import sys
import time
import math
from platform import python_implementation
from ctypes import *
from attrdict import AttrDict
from array import array
import Queue
from threading import Thread
os.environ['PYSDL2_DLL_PATH'] = './libs/SDL2.framework'
from sdl2 import *
import sendhoudini as sh

SCREEN_WIDTH = 200
SCREEN_HEIGHT = 200

running = True
joys = AttrDict()
qEvents = Queue.Queue()
screen = None

def onJoyAxisMotion(e):
    # the instance id
    # Sint16 : -32768 to 32767 mapped to 0.0 to 1.0
    deadzone = 4500
    value = 0.0

    if (e.jaxis.value < deadzone) and (e.jaxis.value > -deadzone):
        value = 0.5
    else:
        if e.jaxis.value > 0:
            value = e.jaxis.value - deadzone
            value = value / (32767.0 - deadzone) * 0.5 + 0.5
        else:
            value = e.jaxis.value + deadzone
            value = value / (32768.0 - deadzone) * 0.5 + 0.5

    joy = joys[e.jaxis.which]
    joy.axis[e.jaxis.axis] = value

def onJoyHatMotion(e):
    pass

def onJoyBallMotion(e):
    pass

def onButtonDown(e):
    joy = joys[e.jbutton.which]
    joy.button[e.jbutton.button] = 1

def onButtonUp(e):
    joy = joys[e.jbutton.which]
    joy.button[e.jbutton.button] = 0

def onKeyDown(e):
    if e.key.keysym.sym == SDLK_ESCAPE:
        quit()

def onJoystickAdded(e):
    # the device index
    index = e.jdevice.which
    print('Joystick added: %d' % index)
    addJoystick(index)

def onJoystickRemoved(e):
    # the instance
    instance = e.jdevice.which
    print('Joystick removed: %d' % instance)
    if instance in joys:
        del joys[instance]

def quit(e=None):
    global running
    running = False

def addJoystick(i):
    joy = SDL_JoystickOpen(i)

    name = SDL_JoystickNameForIndex(i)
    instance = SDL_JoystickInstanceID(joy)

    if instance in joys:
        return

    attached = SDL_JoystickGetAttached(joy)

    # FIXME interperter crash in CPython
    guid = ''
    if not 'CPython' in python_implementation():
        guid = SDL_JoystickGetGUID(joy)
        guid_buff = create_string_buffer(33)
        SDL_JoystickGetGUIDString(guid, guid_buff, sizeof(guid_buff))
        guid = guid_buff.value

    axes = SDL_JoystickNumAxes(joy)
    balls = SDL_JoystickNumBalls(joy)
    hats = SDL_JoystickNumHats(joy)
    buttons = SDL_JoystickNumButtons(joy)

    # check if game controller
    # SDL_IsGameController(i)
    # SDL_GameControllerNameForIndex
    controller = None

    joys[instance] = AttrDict({
        'index': i,
        'joy': joy,
        'name': name or '',
        'attached': lambda self: SDL_JoystickGetAttached(self['joy']),
        'guid': guid,
        'axes': axes,
        'axis' : [0] * axes,
        'balls': balls,
        'hats': hats,
        'buttons': buttons,
        'button' : [0] * buttons,
        'controller': controller
    })

eventType = {
    SDL_JOYAXISMOTION: onJoyAxisMotion,
    SDL_JOYHATMOTION: onJoyHatMotion,
    SDL_JOYBALLMOTION: onJoyBallMotion,
    SDL_JOYBUTTONDOWN: onButtonDown,
    SDL_JOYBUTTONUP: onButtonUp,
    SDL_KEYDOWN: onKeyDown,
    SDL_JOYDEVICEADDED: onJoystickAdded,
    SDL_JOYDEVICEREMOVED: onJoystickRemoved,
    SDL_QUIT: quit
}

def sendHoudini(c):
    try:
        value = qEvents.get(True, 1)
    except Queue.Empty:
        pass
    else:
        sh.sendValue(c, value)
        qEvents.task_done()

def fill(r, g, b, a=SDL_ALPHA_OPAQUE):
    SDL_SetRenderDrawColor(screen, r, g, b, a)

def clear():
    fill(0xA0, 0xA0, 0xA0)
    SDL_RenderClear(screen)

def drawRect(s, x, y, w, h):
    area = SDL_Rect()
    area.x = int(x)
    area.y = int(y)
    area.w = int(w)
    area.h = int(h)
    SDL_RenderFillRect(s, byref(area))

def draw():
    clear()
    fill(0x00, 0x00, 0x00)
    for i in joys:
        joy = joys[i]
        for cord in range(0,len(joy.axis),2):
            drawRect(screen,
                     (joy.axis[cord] * SCREEN_WIDTH) - 8,
                     (joy.axis[cord+1] * SCREEN_HEIGHT) - 8,
                     16,
                     16)

def loop(event):
    while running:
        while SDL_PollEvent(byref(event)):
            eType = event.type
            if eType in eventType:
                eventType[eType](event)

        draw()
        SDL_RenderPresent(screen)
        send = []
        send.extend(joys[0].axis)
        send.extend(joys[0].button)
        qEvents.put(send)

        time.sleep(0.03)

if __name__ == '__main__':
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, '1')
    SDL_SetHint(SDL_HINT_GAMECONTROLLERCONFIG, '1')
    SDL_SetHint(SDL_HINT_ACCELEROMETER_AS_JOYSTICK, '1')

    # video necessary to detect joysticks added/removed
    status = SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)

    if status:
        sys.exit(1)

    SDL_GameControllerAddMappingsFromFile('gamecontrollerdb.txt')

    numJoys = SDL_NumJoysticks()
    for i in range(numJoys):
        addJoystick(i)

    window = SDL_CreateWindow('Joystick', SDL_WINDOWPOS_CENTERED,
                              SDL_WINDOWPOS_CENTERED, SCREEN_WIDTH,
                              SCREEN_HEIGHT, 0)
    screen = SDL_CreateRenderer(window, -1, 0)
    clear()
    SDL_RenderPresent(screen)
    SDL_RaiseWindow(window)

    event = SDL_Event()

    pipe = sh.HoudiniConnection(5000, sendHoudini)
    pipe.start()

    try:
        loop(event)
    except KeyboardInterrupt:
        pass

    pipe.close()
    SDL_DestroyRenderer(screen)
    SDL_DestroyWindow(window)
    SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER)
