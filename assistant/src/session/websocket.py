# websocket_server.py - Enhanced version for multiple modules
import asyncio
import websockets
import json
import threading
from datetime import datetime
import queue
import logging

class ElisaUIController:
    """
    Centralized UI controller that can be accessed from multiple Python modules
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(ElisaUIController, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.connected_clients = set()
            self.server = None
            self.message_queue = queue.Queue()
            self.loop = None
            self.server_thread = None
            self._initialized = True
            
            # Set up logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.connected_clients.add(websocket)
        self.logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
        
        # Send current system status to new client
        await self.send_to_client(websocket, {
            "type": "connection_established",
            "message": "Connected to Elisa Assistant",
            "timestamp": datetime.now().isoformat()
        })
        
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.connected_clients.discard(websocket)
        self.logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")
        
    async def send_to_client(self, client, message):
        """Send message to a specific client"""
        try:
            await client.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            self.connected_clients.discard(client)
            
    async def broadcast_message(self, message):
        """Send message to all connected clients"""
        if self.connected_clients:
            disconnected = set()
            for client in self.connected_clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            
            # Remove disconnected clients
            for client in disconnected:
                self.connected_clients.discard(client)
                
    def _queue_message(self, message):
        """Queue message for sending (thread-safe)"""
        self.message_queue.put(message)
        
    def set_state(self, state, module_name=None):
        """Update UI state - can be called from any thread/module"""
        message = {
            "type": "state_change",
            "state": state,
            "module": module_name or "system",
            "timestamp": datetime.now().isoformat()
        }
        self._queue_message(message)
        
    def add_log(self, level, message, module_name=None):
        """Add log entry to UI - can be called from any thread/module"""
        log_message = {
            "type": "log",
            "level": level,
            "message": message,
            "module": module_name or "system",
            "timestamp": datetime.now().isoformat()
        }
        self._queue_message(log_message)
        
        # Also log to console with module info
        module_prefix = f"[{module_name}] " if module_name else ""
        print(f"[{level.upper()}] {module_prefix}{message}")
        
    def send_custom_data(self, data_type, data, module_name=None):
        """Send custom data to UI - for future extensions"""
        message = {
            "type": data_type,
            "data": data,
            "module": module_name or "system",
            "timestamp": datetime.now().isoformat()
        }
        self._queue_message(message)
        
    async def process_message_queue(self):
        """Process queued messages in the event loop"""
        while True:
            try:
                # Process all messages in queue
                messages_to_send = []
                while not self.message_queue.empty():
                    try:
                        message = self.message_queue.get_nowait()
                        messages_to_send.append(message)
                    except queue.Empty:
                        break
                
                # Send all messages
                for message in messages_to_send:
                    await self.broadcast_message(message)
                    
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
                
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                try:
                    # Handle incoming messages from UI if needed
                    data = json.loads(message)
                    self.logger.info(f"Received from UI: {data}")
                    
                    # You can add UI -> Python communication here
                    # For example, UI sending commands back to Python
                    
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON received: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            await self.unregister_client(websocket)
        
    def start_server(self, host="localhost", port=8765):
        """Start the WebSocket server in a separate thread"""
        if self.server_thread and self.server_thread.is_alive():
            self.logger.warning("Server already running")
            return self.server_thread

        def run_server_loop():
            # Create new event loop for this thread and set it as the current one
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            async def server_main():
                # Start server
                self.server = await websockets.serve(self.handle_client, host, port)
                self.logger.info(f"WebSocket server started on ws://{host}:{port}")

                # Kick off queue processor
                self.loop.create_task(self.process_message_queue())

            try:
                # Run async setup once, then start forever loop
                self.loop.run_until_complete(server_main())
                self.loop.run_forever()
            except Exception as e:
                self.logger.error(f"Server error: {e}")
            finally:
                if self.server:
                    self.server.close()
                    self.loop.run_until_complete(self.server.wait_closed())
                self.loop.close()
                self.logger.info("WebSocket server stopped.")

        self.server_thread = threading.Thread(target=run_server_loop, daemon=True)
        self.server_thread.start()
        return self.server_thread
    
    def stop_server(self):
        """Stop the WebSocket server"""
        if self.server and self.loop and self.loop.is_running():
            self.logger.info("Stopping WebSocket server...")
            # Use call_soon_threadsafe to stop the loop from the main thread
            self.loop.call_soon_threadsafe(self.server.close)
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5) # Wait for the thread to finish
            if self.server_thread.is_alive():
                self.logger.warning("Server thread did not terminate gracefully.")

# Global UI controller instance (Singleton)
ui_controller = ElisaUIController()

# Convenience functions for modules to use
def set_ui_state(state, module_name=None):
    """Set UI state - call this from any module"""
    ui_controller.set_state(state, module_name)
    
def add_ui_log(level, message, module_name=None):
    """Add log to UI - call this from any module"""
    ui_controller.add_log(level, message, module_name)
    
def send_ui_data(data_type, data, module_name=None):
    """Send custom data to UI - call this from any module"""
    ui_controller.send_custom_data(data_type, data, module_name)

# Module registration helper
class UILogger:
    """Helper class for modules to easily integrate with UI"""
    
    def __init__(self, module_name):
        self.module_name = module_name
        
    def set_state(self, state):
        """Set UI state for this module"""
        set_ui_state(state, self.module_name)
        
    def log_info(self, message):
        """Log info message"""
        add_ui_log("info", message, self.module_name)
        
    def log_success(self, message):
        """Log success message"""
        add_ui_log("success", message, self.module_name)
        
    def log_warning(self, message):
        """Log warning message"""
        add_ui_log("warning", message, self.module_name)
        
    def log_error(self, message):
        """Log error message"""
        add_ui_log("error", message, self.module_name)
        
    def send_data(self, data_type, data):
        """Send custom data to UI"""
        send_ui_data(data_type, data, self.module_name)

# Factory function to create module loggers
def create_ui_logger(module_name):
    """Create a UI logger for a specific module"""
    return UILogger(module_name)