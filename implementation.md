YOGURT PROCESSING SYSTEM: FULL-STACK IMPLEMENTATION PLAN
Team: Group 12
Tech Stack: PostgreSQL (Database), Django (Backend), HTML/CSS/Vanilla JS (Frontend)
Goal: Build a lightweight, high-performance web dashboard to showcase our advanced database architecture.

PHASE 1: ENVIRONMENT SETUP AND DATABASE CONNECTION
1. Project Initialization: Set up the Python virtual environment and install Django and the PostgreSQL database adapter.
2. Django Configuration: Create the core Django project and a dedicated dashboard application.
3. Database Binding: Connect Django settings directly to our verified PostgreSQL database. We will bypass the default Django table creation tools to ensure our custom SQL script remains the absolute master of the database structure.

PHASE 2: BACKEND API DEVELOPMENT (DJANGO)
1. Routing Setup: Define the web addresses for our pages and the API endpoints that our frontend will communicate with.
2. Raw SQL Views: Write Python functions that execute raw SQL queries directly against our database. This will include:
   * Queries to fetch live stock levels and active production batches.
   * Insert statements to log new quality control results.
   * Update statements designed to intentionally trigger our database security locks.
3. Error Handling: Ensure the backend captures the specific database exception messages (like the completed batch warning) and passes them cleanly to the frontend.

PHASE 3: FRONTEND INTERFACE DESIGN (HTML AND CSS)
1. Layout Architecture: Build a single-page dashboard using a clean, industrial theme.
2. Component Design:
   * Live Factory Monitor: A section displaying real-time inventory and active machine statuses.
   * Quality Control Panel: A dedicated area for inspectors to approve or reject batches.
   * Security Demonstration Zone: A specific control panel designed to attempt edits on finalized records to visually showcase our immutability triggers.

PHASE 4: JAVASCRIPT INTEGRATION AND INTERACTIVITY
1. Asynchronous Fetching: Write Vanilla JavaScript to request data from our Django backend without reloading the web page, creating a smooth user experience.
2. Event Listeners: Attach click events to dashboard buttons to trigger the backend functions.
3. Notifications: Build a pop-up alert system to display database successes or the custom security errors thrown by our triggers during the presentation.

PHASE 5: SYSTEM TESTING AND PRESENTATION PREPARATION
1. Integration Testing: Run end-to-end tests ensuring that clicking a button on the webpage successfully executes the exact SQL command we expect in the database.
2. Performance Profiling: Verify that the frontend dashboards load instantly, proving that our custom indexes are working correctly.
3. Defense Walkthrough: Prepare a live demonstration script for the presentation, specifically highlighting how the lightweight frontend relies entirely on the heavy lifting done by our PostgreSQL engine.