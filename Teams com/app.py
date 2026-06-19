"""
Team Collaboration Platform - Main Application Entry Point

This is the file you run to start the whole website!
Just type: python app.py
And the website will start on http://localhost:5000

Everything in this file:
- Reads settings from .env file
- Creates the Flask app
- Starts the server with SocketIO (for video calls)
- Prints a welcome message
"""

# Import os to read environment variables (settings)
import os
# Import dotenv to load .env file (SECRET_KEY, DATABASE, etc)
from dotenv import load_dotenv
# Import the create_app function that builds the Flask app
from app import create_app

# Read the .env file (contains all secret settings)
# This file is NOT in Git (security!)
load_dotenv()

# Create the Flask app with all settings, database, routes, etc.
app = create_app()


# This line means: only run this code if this file is executed directly
# NOT if another file imports this file
if __name__ == '__main__':
    # Read from environment: Are we in development or production?
    # Default is 'development' (means debug mode ON)
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    # Read from environment: What port to use?
    # Default is 5000 (means http://localhost:5000)
    port = int(os.getenv('PORT', 5000))
    
    # Import socketio (needed for real-time video call signaling)
    from app import socketio
    
    # Print a pretty welcome message to the terminal
    print(f"""
    ╔════════════════════════════════════════════════════════╗
    ║   Team Collaboration Platform                          ║
    ║                                                        ║
    ║   Starting application...                              ║
    ║   Mode: {'DEBUG' if debug else 'PRODUCTION'}
    ║   URL: http://localhost:{port}                          
    ║                                                        ║
    ║   Press CTRL+C to stop                                ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Start the server using socketio.run() (not app.run())
    # socketio.run() enables real-time features like WebRTC video calls
    socketio.run(
        app,  # The Flask app we created above
        host='0.0.0.0',  # Listen on all network interfaces (accessible from any IP)
        port=port,  # Use the port we read from .env (default 5000)
        debug=debug,  # Enable debug mode if FLASK_ENV is 'development'
        allow_unsafe_werkzeug=True  # Allow werkzeug in development (development only!)
    )
