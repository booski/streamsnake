import os
import random
import threading
import time

from collections import deque

from PIL import Image, ImageOps
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper


class Game:
    def __init__(self, deck, wrap=False):
        self.deck = deck
        self.wrap = wrap
        
        self.rows, self.cols = deck.key_layout()
        self.allPositions = range(0, deck.key_count())

        self.headPic = PILHelper.to_native_format(
            deck, PILHelper.create_image(deck, 'green'))
        self.snakePic = PILHelper.to_native_format(
            deck, PILHelper.create_image(deck, 'white'))
        self.fruitPic = PILHelper.to_native_format(
            deck, PILHelper.create_image(deck, 'red'))
        self.nonePic = PILHelper.to_native_format(
            deck, PILHelper.create_image(deck, 'black'))

        self.segments = deque([8])
        self.direction = 'right'
        self.nextDirection = 'right'
        self.length = 2
        self.fruitPos = self.placeFruit()
        self.speed = 1


    def getCoordinate(self, key):
        return (key % self.cols, key // self.cols)


    def getIndex(self, coord):
        return coord[0] + coord[1]*self.cols


    def draw(self):
        with self.deck:
            for key in self.allPositions:
                if key == self.fruitPos:
                    # This space is a fruit
                    pic = self.fruitPic
                elif key == self.segments[0]:
                    # This space is the snake's head
                    pic = self.headPic
                elif key in self.segments:
                    # This space is part of the snake's tail
                    pic = self.snakePic
                else:
                    # This space is empty
                    pic = self.nonePic
                self.deck.set_key_image(key, pic)


    def update(self):
        alive = True
        nextPos = self.getNext()
        nextIndex = self.getIndex(nextPos)

        # This should always remove (at least) the last tail block,
        # so we can move there without colliding.
        while len(self.segments) >= self.length:
            pos = self.segments.pop()

        # Check for self-collision
        if nextIndex in self.segments:
            alive = False

        # Check for leaving the board
        (nextX, nextY) = nextPos
        if nextX < 0 or nextY < 0:
            alive = False
        if nextX >= self.cols or nextY >= self.rows:
            alive = False
        
        # Update snake position
        self.segments.appendleft(nextIndex)
        self.direction = self.nextDirection

        if not alive:
            return False
            
        # Check for growth
        if nextIndex == self.fruitPos:
            self.length += 1
            self.fruitPos = self.placeFruit()
            self.speed -= 0.1

        return True


    def placeFruit(self):
        options = set(self.allPositions)
        for pos in self.segments:
            options.remove(pos)
        if len(options):
            return random.choice(list(options))
        return None


    def setDirection(self, key):
        (keyX, keyY) = self.getCoordinate(key)
        (headX, headY) = self.getCoordinate(self.segments[0])

        if self.direction == 'right' or self.direction == 'left':
            if keyY < headY:
                self.nextDirection = 'up'
            elif keyY > headY:
                self.nextDirection = 'down'
        elif self.direction == 'up' or self.direction == 'down':
            if keyX < headX:
                self.nextDirection = 'left'
            elif keyX > headX:
                self.nextDirection = 'right'


    def getNext(self):
        (headX, headY) = self.getCoordinate(self.segments[0])
        nextPos = (headX, headY)
        if self.nextDirection == 'right':
            nextPos = (headX + 1, headY)
        elif self.nextDirection == 'left':
            nextPos = (headX - 1, headY)
        elif self.nextDirection == 'down':
            nextPos = (headX, headY + 1)
        elif self.nextDirection == 'up':
            nextPos = (headX, headY - 1)

        if self.wrap:
            (nextX, nextY) = nextPos
            if nextX < 0:
                # right-side overwrap
                nextX = self.cols - 1
            elif nextX >= self.cols:
                # left-side overwrap
                nextX = 0
            if nextY < 0:
                # overwrap up
                nextY = self.rows - 1
            elif nextY >= self.rows:
                # overwrap down
                nextY = 0
            nextPos = (nextX, nextY)

        return nextPos


def key_change_callback(deck, key, state):
    # Only act on keyUp events
    if state == False:
        GAMESTATE.setDirection(key) 


if __name__ == "__main__":
    deck = DeviceManager().enumerate()[0]

    deck.open()
    deck.reset()

    print("Opened '{}' device (serial number: '{}')".format(
        deck.deck_type(), deck.get_serial_number()))

    deck.set_brightness(100)

    GAMESTATE = Game(deck, True)
            
    # Register callback function for when a key state changes.
    deck.set_key_callback(key_change_callback)

    running = True
    while running:
        running = GAMESTATE.update()
        GAMESTATE.draw()
        if not running:
            deck.reset()
            deck.close()
        else:
            time.sleep(GAMESTATE.speed)
    
    # Wait until all application threads have terminated (for this example,
    # this is when all deck handles are closed).
    for t in threading.enumerate():
        try:
            t.join()
        except RuntimeError:
            pass
        
    print("Done")
