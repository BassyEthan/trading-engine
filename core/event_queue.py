from collections import deque
import heapq
from events.base import MarketEvent, SignalEvent, OrderEvent, FillEvent

# Event type priorities for timestamp-ordered processing
# Lower number = higher priority (processed first at same timestamp)
EVENT_PRIORITIES = {
    MarketEvent: 0,   # Market events processed first (update prices)
    SignalEvent: 1,   # Signals generated from market events
    OrderEvent: 2,   # Orders created from signals
    FillEvent: 3,     # Fills complete the cycle (must finish before next timestamp)
}

def get_event_priority(event):
    """Get priority for an event type. Lower number = higher priority."""
    event_type = type(event)
    return EVENT_PRIORITIES.get(event_type, 99)  # Unknown types go last


class EventQueue:
    """
    FIFO event queue (legacy implementation).
    
    This maintains backward compatibility but is deprecated.
    Use PriorityEventQueue for timestamp-ordered processing.
    """

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


class PriorityEventQueue:
    """
    Priority queue that processes events in strict timestamp order.
    
    Events are sorted by (timestamp, event_type_priority) to ensure:
    - All events at timestamp T are processed before T+1
    - Within the same timestamp, events are processed in order:
      MarketEvent → SignalEvent → OrderEvent → FillEvent
    
    This guarantees deterministic event processing and ensures risk checks
    see the correct portfolio state.
    """
    
    def __init__(self):
        # Heap stores (priority, counter, event) tuples
        # Priority = (timestamp, event_type_priority)
        # Counter ensures stable sorting for events with same priority
        self._heap = []
        self._counter = 0
    
    def put(self, event):
        """Add an event to the priority queue."""
        if not hasattr(event, 'timestamp'):
            raise ValueError(f"Event {event} must have a timestamp attribute")
        
        priority = get_event_priority(event)
        # Use (timestamp, priority, counter) for stable sorting
        heapq.heappush(self._heap, (event.timestamp, priority, self._counter, event))
        self._counter += 1
    
    def get(self):
        """Remove and return the next event in timestamp order."""
        if not self._heap:
            raise IndexError("PriorityEventQueue is empty")
        
        # Pop the smallest (earliest timestamp, highest priority)
        _, _, _, event = heapq.heappop(self._heap)
        return event
    
    def is_empty(self):
        """Check if the queue is empty."""
        return len(self._heap) == 0
    
    def __len__(self):
        """Return the number of events in the queue."""
        return len(self._heap)    

