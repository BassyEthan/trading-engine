from core.logger import get_logger

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
        self._handlers = {}

    def register_handler(self, event_type, handler):
        #register a handler for a specific event type.
        if event_type in self._handlers:
            raise ValueError(f"Handler already registered for {event_type}")
        self._handlers[event_type] = handler

    def dispatch(self, event):
        #dispatch an event to its handler
        handler = self._handlers.get(type(event))
        logger.info(f"Dispatching {type(event).__name__}")
        if handler is None:
            return []
        
        result = handler(event)

        if result is None:
            return []
        
        return result
    
    #always returns list of events

