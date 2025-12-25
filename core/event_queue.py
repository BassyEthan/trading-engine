from collections import deque

# This file defines a FIFO event queue that stores Event objects and returns them in the exact order they were received
# Remember event object, and get the next event
# Events are returned in the same order theyx were added.
# The queue does not inspect or modify events
# The queue never drops or reorders events

#conveyor belt!

class EventQueue:

    def __init__(self):
        #deque object is used here instead of list because popping a list is slow, but popleft() from deque is constant time
        self._queue = deque()
        
    def put(self, event):
        #add an event to the end of the queue
        self._queue.append(event)

    def get(self):
        #remove and return the next event in FIFO order
        if not self._queue:
            raise IndexError("EventQueue is empty")
        return self._queue.popleft()

    def is_empty(self):
        #is queue empty?
        return len(self._queue) == 0    

