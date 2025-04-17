# Bluesky List Migrator

A simple tool built with Python and Streamlit to copy members from a user list on one Bluesky account (Account A) to a **new** user list on a different Bluesky account (Account B).

This is useful if you are migrating accounts or want to duplicate a list structure under a new identity.

Useful for user list and moderation lists (aka blocklists)!

## Key Features

*   Connects securely to two different Bluesky accounts using App Passwords.
*   Fetches all members from a specified list URI on the source account.
*   Creates a new list (curation or moderation) on the destination account with a custom name and description.
*   Adds the fetched members to the newly created list on the destination account.
*   Provides a simple web interface for easy use.

## Security

*   This tool requires **App Passwords**. You can generate these specifically for this tool in your Bluesky account settings (Settings -> App Passwords).

## Requirements

*   Python 3.10+ (developed with 3.12 as specified in `.python-version`)
*   `pip` (Python package installer)
*   Git (optional, for cloning the repository)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/igor-sx-bluesky_migration_tools.git
    cd igor-sx-bluesky_migration_tools
    ```
    (Replace `your-username` with the actual location if applicable)

2.  **(Recommended) Create and activate a virtual environment:**
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *(This keeps the installed packages separate from your system Python installation.)*

3.  **Install dependencies:**
    ```bash
    pip install streamlit atproto
    ```

## Running the Tool

1.  **Ensure your virtual environment is activated** (if you created one).
2.  **Navigate to the project directory** in your terminal.
3.  **Run the Streamlit app:**
    ```bash
    streamlit run mig.py
    ```
4.  This command will output a URL (usually `http://localhost:8501`) and should automatically open the tool in your default web browser.
5.  **Fill in the details in the web interface:**
    *   **Source Account (A):** Handle, App Password, and the AT URI of the list you want to copy.
        *   *Finding the AT URI:* Go to the list's page on the Bluesky web app (e.g., `https://bsky.app/profile/did:plc:abc.../lists/at://did:plc:abc.../app.bsky.graph.list/xyz...`). The AT URI is the part starting with `at://...`.
    *   **Destination Account (B):** Handle, App Password, the desired name for the *new* list, its purpose (Curation or Moderation), and an optional description.
6.  **Click the "Migrate List" button.**
7.  The tool will show progress updates for logging in, fetching members, creating the new list, and adding members. Be patient, especially when adding members to large lists, as there are delays between additions to respect API rate limits.

## Rate limiting

Rate limiting is currently rudimentary, handled via simple time delays: a fixed time.sleep(0.2) follows each successful list item createRecord call. 
Any exception during member addition triggers a longer time.sleep(1.0) before continuing.

## Roadmap / Future Improvements

*   **Add Members to Existing List:** Option to add members to an already existing list on Account B instead of only creating a new one.
*   **Batch Member Addition:** Use `com.atproto.repo.applyWrites` for potentially faster and more efficient addition of members, reducing the chance of hitting rate limits compared to adding one by one.
*   **Improved Error Handling:** Provide more specific feedback on API errors (e.g., distinguish rate limits from invalid URIs).
*   **List Metadata Copying:** Option to copy the source list's description or avatar (if set) to the new list.
*   **UI Enhancements:** Maybe preview members before adding, clearer progress indicators for very large lists.
*   **Migrate Multiple Lists:** Add functionality to select and migrate multiple lists in one go.
*   **Migrate more stuff** like follows

## Disclaimer

This tool interacts with the official Bluesky API. Use it responsibly. The author is not responsible for any issues arising from the use of this tool, including accidental data loss or account restrictions. Always use App Passwords for security.
