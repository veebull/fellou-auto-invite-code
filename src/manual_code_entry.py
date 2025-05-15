#!/usr/bin/env python3
# Simple Discord API client that shows codes but requires manual entry
# This version doesn't use pyautogui or AppleScript to avoid permission issues

import requests
import json
import os
import time
import re
import subprocess
import argparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
TARGET_GUILD_ID = "1320757665118556160"
TARGET_CHANNEL_ID = "1321156950486028378"
CHANNEL_URL = f"https://discord.com/channels/{TARGET_GUILD_ID}/{TARGET_CHANNEL_ID}"
TARGET_APP_NAME = "Fellou"  # App where invite codes will be entered manually
# Updated regex pattern to match only 6-character uppercase alphanumeric codes that appear as separate words
INVITE_PATTERN = r'\b[A-Z0-9]{6}\b'  # Pattern to match codes like "CDNQ4Q", "6QYAUV", etc.

# User filter lists
# Ban list: Messages from these user IDs will be ignored (add user IDs as strings)
BAN_LIST = [
    # Example: "123456789012345678",
    # Add more banned user IDs here
]

# Whitelist: If not empty, ONLY messages from these user IDs will be processed
# (overrides the ban list if populated)
WHITELIST = [
    # Example: "987654321098765432",
    # Add whitelisted user IDs here
]

# Current user ID (for auto-whitelisting)
CURRENT_USER_ID = ""  # Fill this with your user ID if you want to auto-whitelist yourself

# If you have a token, you can set it here. Otherwise, it will prompt for login
TOKEN_FILE = "discord_token.txt"

# Keep track of processed messages/codes
processed_msg_ids = set()
processed_codes = set()

# Create a session with retry logic
def create_session_with_retries(retries=5, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504)):
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(['GET', 'POST']),
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def save_token(token):
    """Save Discord token to file"""
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)
    print(f"Token saved to {TOKEN_FILE}")

def load_token():
    """Load Discord token from file if available"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return f.read().strip()
    return None

def login_to_discord(email, password):
    """Login to Discord and get a token (note: this is against Discord's TOS)"""
    print("Attempting to login to Discord via API...")
    
    # Discord login API endpoint
    url = "https://discord.com/api/v9/auth/login"
    
    # Prepare login data
    data = {
        "login": email,
        "password": password,
        "undelete": False,
        "captcha_key": None,
        "login_source": None,
        "gift_code_sku_id": None
    }
    
    # Set headers to mimic browser
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    }
    
    # Create a session with retry logic
    session = create_session_with_retries()
    
    try:
        # Send login request
        response = session.post(url, json=data, headers=headers, timeout=15)
        
        # Check if login was successful
        if response.status_code == 200:
            token = response.json().get("token")
            if token:
                print("Login successful!")
                save_token(token)
                return token
        
        # Handle 2FA if needed
        if response.status_code == 400 and "mfa" in response.json().get("message", "").lower():
            print("Two-factor authentication required")
            ticket = response.json().get("ticket")
            code = input("Enter your 2FA code: ")
            
            # Submit 2FA code
            mfa_url = "https://discord.com/api/v9/auth/mfa/totp"
            mfa_data = {
                "code": code,
                "ticket": ticket,
                "login_source": None,
                "gift_code_sku_id": None
            }
            
            mfa_response = session.post(mfa_url, json=mfa_data, headers=headers, timeout=15)
            
            if mfa_response.status_code == 200:
                token = mfa_response.json().get("token")
                if token:
                    print("2FA login successful!")
                    save_token(token)
                    return token
        
        print(f"Login failed: {response.status_code} - {response.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error during login: {e}")
        print("This might be a temporary issue. Please try again in a few minutes.")
        return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None

def get_user_token():
    """Get Discord token from file or user input"""
    token = load_token()
    if token:
        print("Using saved Discord token")
        return token
    
    # Prompt for login credentials
    print("Discord token not found. Please log in:")
    email = input("Email: ")
    password = input("Password: ")
    
    # Authenticate and get token
    token = login_to_discord(email, password)
    if not token:
        print("Could not obtain Discord token. Please check your credentials.")
        exit(1)
    
    return token

def get_channel_messages(token, limit=20, before=None):
    """Fetch messages from the target Discord channel"""
    url = f"https://discord.com/api/v9/channels/{TARGET_CHANNEL_ID}/messages"
    
    # Set query parameters
    params = {"limit": limit}
    if before:
        params["before"] = before
    
    # Set up headers with auth token
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    }
    
    # Create a session with retry logic
    session = create_session_with_retries()
    
    try:
        # Make request to Discord API
        response = session.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("Token expired or invalid. Please log in again.")
            # Delete the token file so we can get a new one
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            return None
        else:
            print(f"Error fetching messages: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error occurred: {e}")
        print("This might be a temporary network issue or Discord API rate limiting")
        print("Waiting 10 seconds before retrying...")
        time.sleep(10)
        return None
    except requests.exceptions.Timeout:
        print("Request timed out. Discord API might be slow or unavailable.")
        print("Waiting 10 seconds before retrying...")
        time.sleep(10)
        return None
    except Exception as e:
        print(f"Unexpected error when fetching messages: {e}")
        print("Waiting 5 seconds before retrying...")
        time.sleep(5)
        return None

def get_current_user_info(token):
    """Get current user information using the token"""
    url = "https://discord.com/api/v9/users/@me"
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    }
    
    try:
        # Create a session with retry logic
        session = create_session_with_retries()
        
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get("id")
            username = user_data.get("username")
            print(f"Logged in as: {username} (ID: {user_id})")
            return user_id, username
        else:
            print(f"Failed to get user info: {response.status_code} - {response.text}")
            return None, None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error getting user info: {e}")
        print("Waiting 5 seconds before retrying...")
        time.sleep(5)
        return None, None
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None, None

def find_invite_codes(content):
    """Find potential invite codes in message content"""
    if not content:
        return []
    
    return re.findall(INVITE_PATTERN, content)

def notify_user(code):
    """Notify user about the code with a visible alert"""
    try:
        # Try to show a message using terminal bell and text formatting
        print("\n" + "=" * 60)
        print(f"\033[1;32m!!! NEW CODE FOUND: {code} !!!\033[0m")
        print(f"Please enter this code in {TARGET_APP_NAME} now!")
        print("=" * 60 + "\n")
        
        # Make a terminal bell sound
        print("\a")
        
        # Try to switch to the app without sending keystrokes
        try:
            subprocess.run(['osascript', '-e', f'tell application "{TARGET_APP_NAME}" to activate'])
            print(f"Switched focus to {TARGET_APP_NAME}. Please enter the code manually.")
        except:
            print(f"Please manually switch to {TARGET_APP_NAME} and enter the code.")
        
        # Ask user for confirmation
        confirmation = input("Press Enter after you've entered the code (or type 'skip' to ignore this code): ")
        if confirmation.lower().strip() == 'skip':
            print(f"Skipped code: {code}")
            return False
        else:
            print(f"Confirmation received for code: {code}")
            return True
    
    except Exception as e:
        print(f"Error in notification: {e}")
        print(f"IMPORTANT! New code found: {code}")
        return False

def process_messages(messages):
    """Process messages to find invite codes"""
    if not messages:
        return
    
    # Add current user to whitelist if specified and not already there
    if CURRENT_USER_ID and CURRENT_USER_ID not in WHITELIST:
        WHITELIST.append(CURRENT_USER_ID)
        print(f"Auto-whitelisted current user ID: {CURRENT_USER_ID}")
    
    new_codes_found = False
    
    for msg in messages:
        # Skip if we've already processed this message
        msg_id = msg.get("id")
        if msg_id in processed_msg_ids:
            continue
        
        # Get user ID for filtering
        user_id = msg.get("author", {}).get("id", "")
        username = msg.get("author", {}).get("username", "Unknown")
        
        # Apply filtering rules:
        # 1. If whitelist exists (not empty), only process messages from whitelisted users
        # 2. If whitelist is empty, process messages from all users except those in the ban list
        
        # Check if user is banned
        if user_id in BAN_LIST:
            print(f"Skipping message from banned user: {username} ({user_id})")
            processed_msg_ids.add(msg_id)  # Mark as processed
            continue
            
        # Check whitelist (if it exists)
        if WHITELIST and user_id not in WHITELIST:
            # Skip silently - message is not from a whitelisted user
            processed_msg_ids.add(msg_id)  # Mark as processed anyway
            continue
        
        # Mark as processed
        processed_msg_ids.add(msg_id)
        
        # Get message info
        content = msg.get("content", "")
        author = msg.get("author", {}).get("username", "Unknown")
        timestamp = msg.get("timestamp", "")
        
        # Print message details
        print(f"\nNew message from {author} (ID: {user_id}) at {timestamp}:")
        print(f"Content: {content}")
        
        # Check for invite codes
        invite_codes = find_invite_codes(content)
        if invite_codes:
            print(f"Found potential invite code(s): {', '.join(invite_codes)}")
            
            # Process each code
            for code in invite_codes:
                if code not in processed_codes:
                    print(f"New invite code detected: {code}")
                    if notify_user(code):
                        processed_codes.add(code)
                        new_codes_found = True
    
    return new_codes_found

def monitor_channel(poll_interval=5):
    """Monitor the Discord channel for new messages and invite codes"""
    print(f"Starting Discord channel monitor for: {CHANNEL_URL}")
    print(f"This version will show codes for you to manually enter in {TARGET_APP_NAME}")
    print("=" * 70)
    print("NOTE: This script will NOT try to automatically type codes.")
    print("You'll be notified when a new code is found and need to enter it yourself.")
    print(f"Polling interval: {poll_interval} seconds")
    print("=" * 70)
    
    # Get authentication token
    token = get_user_token()
    
    # Get and save current user ID for auto-whitelisting
    global CURRENT_USER_ID
    if not CURRENT_USER_ID:
        user_id, username = get_current_user_info(token)
        if user_id:
            CURRENT_USER_ID = user_id
            print(f"Current user {username} will be automatically whitelisted")
            if WHITELIST and user_id not in WHITELIST:
                WHITELIST.append(user_id)
                print(f"Added current user to whitelist: {user_id}")
            # Save user ID to file
            save_user_lists()
    
    # Print filter settings
    if WHITELIST:
        print(f"Whitelist active: Only processing messages from {len(WHITELIST)} users")
    if BAN_LIST:
        print(f"Ban list active: Ignoring messages from {len(BAN_LIST)} users")
    
    last_check_time = 0
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    try:
        while True:
            # Check if it's time to poll for new messages
            current_time = time.time()
            if current_time - last_check_time >= poll_interval:
                print(f"\nChecking for new messages... ({time.strftime('%H:%M:%S')})")
                
                # Fetch latest messages
                messages = get_channel_messages(token)
                
                if messages:
                    process_messages(messages)
                    consecutive_errors = 0  # Reset error counter on success
                else:
                    # If we couldn't get messages, we may need to re-authenticate
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"Too many consecutive errors ({consecutive_errors}). Attempting to refresh token...")
                        if os.path.exists(TOKEN_FILE):
                            os.remove(TOKEN_FILE)
                        token = get_user_token()
                        consecutive_errors = 0  # Reset after token refresh
                        
                    # Increase wait time proportionally to consecutive errors
                    wait_time = poll_interval * (1 + consecutive_errors)
                    print(f"Will retry in {wait_time} seconds...")
                    time.sleep(wait_time)
                
                last_check_time = current_time
            
            # Sleep to avoid excessive API calls
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Manual Discord Code Entry Client')
    parser.add_argument('--interval', type=int, default=5, help='Polling interval in seconds (default: 5)')
    
    # User filtering options
    parser.add_argument('--ban', type=str, help='Add a user ID to the ban list')
    parser.add_argument('--unban', type=str, help='Remove a user ID from the ban list')
    parser.add_argument('--whitelist', type=str, help='Add a user ID to the whitelist')
    parser.add_argument('--unwhitelist', type=str, help='Remove a user ID from the whitelist')
    parser.add_argument('--list-filters', action='store_true', help='List current ban list and whitelist')
    
    return parser.parse_args()

def save_user_lists():
    """Save ban list and whitelist to a file"""
    filter_file = "user_filters.json"
    try:
        with open(filter_file, 'w') as f:
            json.dump({
                "ban_list": BAN_LIST,
                "whitelist": WHITELIST,
                "current_user_id": CURRENT_USER_ID
            }, f, indent=2)
        print(f"Saved user filters to {filter_file}")
    except Exception as e:
        print(f"Error saving user filters: {e}")

def load_user_lists():
    """Load ban list and whitelist from a file"""
    filter_file = "user_filters.json"
    global BAN_LIST, WHITELIST, CURRENT_USER_ID
    
    if os.path.exists(filter_file):
        try:
            with open(filter_file, 'r') as f:
                data = json.load(f)
                BAN_LIST = data.get("ban_list", [])
                WHITELIST = data.get("whitelist", [])
                if not CURRENT_USER_ID:  # Don't override if already set
                    CURRENT_USER_ID = data.get("current_user_id", "")
            print(f"Loaded user filters from {filter_file}")
        except Exception as e:
            print(f"Error loading user filters: {e}")

def manage_user_lists(args):
    """Manage ban list and whitelist based on command line arguments"""
    global BAN_LIST, WHITELIST
    changes_made = False
    
    # Load existing lists
    load_user_lists()
    
    # Process ban/unban
    if args.ban:
        if args.ban not in BAN_LIST:
            BAN_LIST.append(args.ban)
            print(f"Added user ID {args.ban} to ban list")
            changes_made = True
        else:
            print(f"User ID {args.ban} is already in ban list")
    
    if args.unban:
        if args.unban in BAN_LIST:
            BAN_LIST.remove(args.unban)
            print(f"Removed user ID {args.unban} from ban list")
            changes_made = True
        else:
            print(f"User ID {args.unban} is not in ban list")
    
    # Process whitelist/unwhitelist
    if args.whitelist:
        if args.whitelist not in WHITELIST:
            WHITELIST.append(args.whitelist)
            print(f"Added user ID {args.whitelist} to whitelist")
            changes_made = True
        else:
            print(f"User ID {args.whitelist} is already in whitelist")
    
    if args.unwhitelist:
        if args.unwhitelist in WHITELIST:
            WHITELIST.remove(args.unwhitelist)
            print(f"Removed user ID {args.unwhitelist} from whitelist")
            changes_made = True
        else:
            print(f"User ID {args.unwhitelist} is not in whitelist")
    
    # List current filters if requested
    if args.list_filters or changes_made:
        print("\nCurrent User Filters:")
        print(f"Current User ID: {CURRENT_USER_ID or 'Not set'}")
        print(f"Ban List ({len(BAN_LIST)} users):")
        for user_id in BAN_LIST:
            print(f"  - {user_id}")
        print(f"Whitelist ({len(WHITELIST)} users):")
        for user_id in WHITELIST:
            print(f"  - {user_id}")
        print("")
    
    # Save changes if any were made
    if changes_made:
        save_user_lists()
    
    return changes_made

def main():
    """Main entry point"""
    args = parse_args()
    
    # Load user lists
    load_user_lists()
    
    # Check if we're just managing user lists
    list_management_args = args.ban or args.unban or args.whitelist or args.unwhitelist or args.list_filters
    if list_management_args:
        changes_made = manage_user_lists(args)
        if list_management_args and not args.interval:  # If only managing lists without other actions, exit
            return
    
    # Start the monitor
    monitor_channel(args.interval)

if __name__ == "__main__":
    main() 