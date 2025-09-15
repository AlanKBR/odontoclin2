"""
Script to run the OdontoClin application and make it accessible externally.
"""

# Import the application factory function
from app import create_app  # pylint: disable=import-self

# Create the application instance
app = create_app()

if __name__ == "__main__":
    # Run the app on 0.0.0.0 to make it accessible externally
    # and on port 1337 as requested.
    # Turn off debug mode for a public-facing app for security.
    app.run(host="0.0.0.0", port=1337, debug=False)
