import streamlit as st
import time
from datetime import datetime, timezone
from atproto import Client, models
from atproto.exceptions import AtProtocolError

# --- Core Migration Logic ---

def get_list_members(client: Client, list_uri: str) -> list[str] | None:
    """Fetches all member DIDs from a given list URI."""
    members = []
    cursor = None
    try:
        while True:
            params = models.AppBskyGraphGetList.Params(
                list=list_uri, limit=100, cursor=cursor
            )
            response = client.app.bsky.graph.get_list(params)
            if not response or not response.items:
                break
            for item in response.items:
                members.append(item.subject.did)
            cursor = response.cursor
            if not cursor:
                break
            # Small delay to be kind to the API
            time.sleep(0.1)
        return members
    except AtProtocolError as e:
        st.error(f"Error fetching list members from {list_uri}: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching members: {e}")
        return None


def create_new_list(
    client: Client, name: str, description: str, purpose: str
) -> str | None:
    """Creates a new list record on the target account."""
    try:
        # Ensure purpose is a valid NSID format if coming from selectbox
        if not purpose.startswith("app.bsky.graph.defs#"):
             purpose = f"app.bsky.graph.defs#{purpose}"

        list_record = models.AppBskyGraphList.Record(
            name=name,
            purpose=purpose,
            description=description,
            createdAt=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            # You could add facets for description here if needed
            # avatar=None # Add avatar blob logic if desired
        )
        response = client.com.atproto.repo.create_record(
            models.ComAtprotoRepoCreateRecord.Data(
                repo=client.me.did, # Use the client's authenticated DID
                collection=models.ids.AppBskyGraphList,
                record=list_record,
            )
        )
        st.success(f"Successfully created new list: {response.uri}")
        return response.uri
    except AtProtocolError as e:
        st.error(f"Error creating new list: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while creating the list: {e}")
        return None


def add_members_to_list(
    client: Client, list_uri: str, members: list[str]
) -> tuple[int, int]:
    """Adds members to the specified list, one by one."""
    success_count = 0
    fail_count = 0
    total = len(members)
    progress_bar = st.progress(0, text=f"Adding members (0/{total})...")

    for i, member_did in enumerate(members):
        try:
            list_item_record = models.AppBskyGraphListitem.Record(
                subject=member_did,
                list=list_uri,
                createdAt=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
            client.com.atproto.repo.create_record(
                models.ComAtprotoRepoCreateRecord.Data(
                    repo=client.me.did, # Use the client's authenticated DID
                    collection=models.ids.AppBskyGraphListitem,
                    record=list_item_record,
                )
            )
            success_count += 1
            # Small delay to avoid rate limits
            time.sleep(0.2)
        except AtProtocolError as e:
            st.warning(f"Failed to add member {member_did}: {e}")
            fail_count += 1
            # Longer delay if we hit an error, might be rate limit
            time.sleep(1)
        except Exception as e:
            st.warning(f"Unexpected error adding member {member_did}: {e}")
            fail_count += 1
            time.sleep(1)
        finally:
             # Update progress bar
             progress = (i + 1) / total
             progress_bar.progress(progress, text=f"Adding members ({i+1}/{total})... {fail_count} failed.")

    progress_bar.empty() # Clear the progress bar on completion
    return success_count, fail_count


# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.title("Bluesky List Migrator")
st.warning(
    "**Security Warning:** This tool requires App Passwords. "
    "**NEVER** enter your main account password. "
    "Generate App Passwords in Bluesky Settings specifically for this tool. "
    "Consider revoking them after use."
)
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("Source Account (Account A)")
    source_handle = st.text_input("Account A Handle (e.g., user.bsky.social)", key="source_handle")
    source_password = st.text_input(
        "Account A App Password", type="password", key="source_password",
        help="Create in Settings -> App Passwords. DO NOT use your main password."
    )
    source_list_uri = st.text_input(
        "Source List AT URI",
        key="source_list_uri",
        placeholder="at://did:plc:xxxxxxxxxxxx/app.bsky.graph.list/xxxxxxxxxxxxx",
        help="Find this by viewing the list on the web and copying the URL, then extracting the AT URI part."
    )

with col2:
    st.header("Destination Account (Account B)")
    dest_handle = st.text_input("Account B Handle (e.g., otheruser.bsky.social)", key="dest_handle")
    dest_password = st.text_input(
        "Account B App Password", type="password", key="dest_password",
        help="Create in Settings -> App Passwords. DO NOT use your main password."
    )
    dest_list_name = st.text_input("New List Name (on Account B)", key="dest_list_name", max_chars=64)
    dest_list_purpose = st.selectbox(
        "New List Purpose",
        options=["curatelist", "modlist"], # referencelist is less common for direct creation
        key="dest_list_purpose",
        index=0, # Default to curation list
        format_func=lambda x: x.replace("list", " List").title(), # Nicer display names
        help="Curation lists are for feeds/discovery. Moderation lists are for bulk mute/block."
    )

    dest_list_desc = st.text_area(
        "New List Description (Optional)", key="dest_list_desc", max_chars=300
    )


st.markdown("---")

if st.button("Migrate List", type="primary"):
    # Basic validation
    if not (source_handle and source_password and source_list_uri and
            dest_handle and dest_password and dest_list_name and dest_list_purpose):
        st.error("Please fill in all required fields.")
    else:
        source_client = Client()
        dest_client = Client()
        members_to_add = None
        new_list_uri = None
        migration_ok = True

        # 1. Login to Source Account
        with st.status("Logging into Source Account (Account A)...", expanded=True) as status_a:
            try:
                st.write(f"Attempting login for {source_handle}...")
                source_client.login(source_handle, source_password)
                st.write(f"Logged in as {source_client.me.handle} ({source_client.me.did})")
                status_a.update(label="Login Successful!", state="complete", expanded=False)
            except AtProtocolError as e:
                st.error(f"Login failed for Account A: {e}")
                migration_ok = False
                status_a.update(label="Login Failed!", state="error", expanded=True)
            except Exception as e:
                st.error(f"An unexpected error occurred during Account A login: {e}")
                migration_ok = False
                status_a.update(label="Login Failed!", state="error", expanded=True)

        # 2. Fetch Members from Source List
        if migration_ok:
            with st.status(f"Fetching members from list {source_list_uri}...", expanded=True) as status_fetch:
                members_to_add = get_list_members(source_client, source_list_uri)
                if members_to_add is not None:
                    st.write(f"Found {len(members_to_add)} members in the source list.")
                    status_fetch.update(label="Fetched Members Successfully!", state="complete", expanded=False)
                else:
                    st.error("Failed to fetch members. Cannot continue.")
                    migration_ok = False
                    status_fetch.update(label="Fetching Members Failed!", state="error", expanded=True)

        # 3. Login to Destination Account
        if migration_ok:
             with st.status("Logging into Destination Account (Account B)...", expanded=True) as status_b:
                try:
                    st.write(f"Attempting login for {dest_handle}...")
                    dest_client.login(dest_handle, dest_password)
                    st.write(f"Logged in as {dest_client.me.handle} ({dest_client.me.did})")
                    status_b.update(label="Login Successful!", state="complete", expanded=False)
                except AtProtocolError as e:
                    st.error(f"Login failed for Account B: {e}")
                    migration_ok = False
                    status_b.update(label="Login Failed!", state="error", expanded=True)
                except Exception as e:
                    st.error(f"An unexpected error occurred during Account B login: {e}")
                    migration_ok = False
                    status_b.update(label="Login Failed!", state="error", expanded=True)

        # 4. Create New List on Destination Account
        if migration_ok:
            with st.status(f"Creating new list '{dest_list_name}' on Account B...", expanded=True) as status_create:
                new_list_uri = create_new_list(
                    dest_client, dest_list_name, dest_list_desc, dest_list_purpose
                )
                if new_list_uri:
                    st.write(f"New list created with URI: {new_list_uri}")
                    status_create.update(label="List Creation Successful!", state="complete", expanded=False)
                else:
                    st.error("Failed to create the new list. Cannot continue.")
                    migration_ok = False
                    status_create.update(label="List Creation Failed!", state="error", expanded=True)

        # 5. Add Members to New List
        if migration_ok and members_to_add and new_list_uri:
            st.info(f"Starting to add {len(members_to_add)} members to the new list. This may take a while...")
            success, failed = add_members_to_list(dest_client, new_list_uri, members_to_add)
            st.success(f"Finished adding members. Successfully added: {success}, Failed: {failed}")
            st.balloons()
        elif migration_ok:
            st.warning("No members found in the source list or new list wasn't created. Nothing to add.")

        if not migration_ok:
            st.error("Migration process stopped due to errors.")