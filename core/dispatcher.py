from core.logger import get_logger
from collections import defaultdict

logger = get_logger("DISPATCHER")

class Dispatcher:
    """
    Routes events to one registered handler based on event type. 

    It's responsibilities are:
        maintain event_type to handler mapping
        dispatch events to the correct handler
        fail fast if the event has no handler
        no business logic
        each event type has one handler
    
    """

    #routes events to the correct handler - which is a function that nows how to react to exactly one type of event

    def __init__(self):
        #handlers are functions whose job is to react to one specific type of event
        self._handlers = defaultdict(list)

    def register_handler(self, event_type, handler):
        #register a handler for a specific event type.
        self._handlers[event_type].append(handler)
        logger.info(
            f"Registered handler {handler.__qualname__} "
            f"for event {event_type.__name__}"
        )

    def dispatch(self, event):
        #dispatch an event to its handler
        handlers = self._handlers.get(type(event), [])
        logger.info(
            f"Dispatching {type(event).__name__} "
            f"to {len(handlers)} handlers(s)"
        )

        new_events = []

        for handler in handlers:
            result = handler(event)
            if result:
                new_events.extend(result)

        return new_events
        
        
    
    #always returns list of events

