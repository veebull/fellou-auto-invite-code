#!/usr/bin/env python3
# Discord API Client for fetching messages from a specific channel

import requests
import json
import os
import time
import re
import pyautogui
import subprocess
import sys
import argparse
import platform
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Get the operating system
OPERATING_SYSTEM = platform.system()  # 'Windows', 'Darwin' (macOS), or 'Linux'

# Configuration
TARGET_GUILD_ID = "1320757665118556160"
TARGET_CHANNEL_ID = "1321156950486028378"
CHANNEL_URL = f"https://discord.com/channels/{TARGET_GUILD_ID}/{TARGET_CHANNEL_ID}"
TARGET_APP_NAME = "Fellou"  # App where invite codes will be entered
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

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Discord API Client')
    parser.add_argument('--test', action='store_true', help='Test code input functionality')
    parser.add_argument('--code', type=str, help='Specific code to test with --test mode')
    parser.add_argument('--interval', type=int, default=5, help='Polling interval in seconds (default: 5)')
    
    # User filtering options
    parser.add_argument('--ban', type=str, help='Add a user ID to the ban list')
    parser.add_argument('--unban', type=str, help='Remove a user ID from the ban list')
    parser.add_argument('--whitelist', type=str, help='Add a user ID to the whitelist')
    parser.add_argument('--unwhitelist', type=str, help='Remove a user ID from the whitelist')
    parser.add_argument('--list-filters', action='store_true', help='List current ban list and whitelist')
    
    return parser.parse_args()

def save_token(token):
    """Save the Discord token to a file"""
    with open(TOKEN_FILE, "w") as f:
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
    """Get the user's Discord token or prompt for login"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token = f.read().strip()
            # Validate token before returning it
            user_id, _ = get_current_user_info(token)
            if user_id:
                return token
    
    # If no token file or token is invalid, prompt for login
    print("Discord token not found or invalid. Please log in:")
    email = input("Email: ")
    password = input("Password: ")
    
    return login_to_discord(email, password)

def get_channel_messages(token, limit=50, before=None):
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
    
    # Make request to Discord API with error handling
    try:
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

def find_invite_codes(content):
    """Find potential invite codes in message content"""
    if not content:
        return []
    
    return re.findall(INVITE_PATTERN, content)

def process_messages(messages):
    """Process messages to find and use invite codes"""
    if not messages:
        return
    
    # Add current user to whitelist if specified and not already there
    if CURRENT_USER_ID and CURRENT_USER_ID not in WHITELIST:
        WHITELIST.append(CURRENT_USER_ID)
        print(f"Auto-whitelisted current user ID: {CURRENT_USER_ID}")
    
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
                    print(f"Using new invite code: {code}")
                    input_code_to_app(code)
                    processed_codes.add(code)

def input_code_to_app(code):
    """Input the code to the target application with input field focus"""
    try:
        print(f"Attempting to input code '{code}' to {TARGET_APP_NAME}...")
        
        # Platform-specific implementation
        if OPERATING_SYSTEM == "Darwin":  # macOS
            input_code_macos(code)
        elif OPERATING_SYSTEM == "Windows":  # Windows
            input_code_windows(code)
        else:
            print(f"Unsupported operating system: {OPERATING_SYSTEM}")
            print(f"\nPlease manually enter this code: {code}")
        
        print("\nAttempted to enter code: " + code)
        
    except Exception as e:
        print(f"Error inputting code: {e}")
        print("Detailed error information:")
        import traceback
        traceback.print_exc()

def input_code_macos(code):
    """Input code on macOS systems"""
    # First activate the target application
    print("Activating target application on macOS...")
    subprocess.run(['osascript', '-e', f'tell application "{TARGET_APP_NAME}" to activate'])
    
    # Wait for app to come to foreground
    time.sleep(1.0)  # Increased wait time
    
    print("IMPORTANT: If you see permission errors like 'Sending keystrokes is not permitted/allowed (1002)':")
    print("1. Go to System Preferences/Settings > Security & Privacy/Privacy > Accessibility")
    print("2. Add your terminal app (Terminal or iTerm) to the list of allowed apps")
    print("3. Also add Python or your code editor if you're running from there")
    print("4. You might need to restart your terminal or editor after making these changes")
    
    # Method 3: Using key codes in AppleScript (may bypass some permission issues)
    print("\nMethod 3: Using AppleScript with key codes...")
    try:
        # Using key codes instead of keystroke command
        keycode_script = f'''
        tell application "{TARGET_APP_NAME}" to activate
        delay 1

        tell application "System Events"
            key code 48 -- Tab
            delay 0.5
            keystroke "{code}"
            delay 0.5
            key code 48 -- Tab again
            delay 0.5
            key code 48 -- Tab again
            delay 0.5
            key code 49 -- Space to "press" button
            delay 0.5
            key code 48 -- Tab again
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', keycode_script], capture_output=True, text=True)
        
        if result.stdout:
            print(f"Key code AppleScript result: {result.stdout.strip()}")
        
        if result.stderr:
            print(f"Key code AppleScript error: {result.stderr.strip()}")
            
            # Check for permission error
            if "not permitted" in result.stderr or "not allowed" in result.stderr or "1002" in result.stderr:
                print("\n⚠️ PERMISSION ERROR DETECTED ⚠️")
                print("You need to allow your terminal app to control your computer.")
                print("Please follow these steps:")
                print("1. Open System Preferences/Settings")
                print("2. Go to Security & Privacy/Privacy > Accessibility")
                print("3. Click the lock icon to make changes")
                print("4. Add your terminal app (Terminal/iTerm) to the list")
                print("5. Restart your terminal and try again")
        else:
            print("Key code method executed without errors!")
            return  # Success! Skip other methods
    except Exception as e:
        print(f"Key code method failed: {e}")
    
    # Try different methods for inputting the code, starting with direct pyautogui
    print("\nMethod 1: Using PyAutoGUI directly...")
    try:
        # Type the code
        pyautogui.typewrite(code)
        time.sleep(0.5)
        
        # Press Enter to submit
        pyautogui.press('return')
        
        print("PyAutoGUI method completed")
    except Exception as e:
        print(f"PyAutoGUI method failed: {e}")
    
    # Try AppleScript method
    print("\nMethod 2: Using AppleScript with keystroke...")
    try:
        # Use a simpler AppleScript approach that's less likely to trigger permission issues
        simple_script = f'''
        tell application "{TARGET_APP_NAME}"
            activate
        end tell
        delay 1
        tell application "System Events"
            keystroke "{code}"
            delay 0.5
            keystroke return
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', simple_script], capture_output=True, text=True)
        
        if result.stdout:
            print(f"AppleScript result: {result.stdout.strip()}")
        
        if result.stderr:
            print(f"AppleScript error: {result.stderr.strip()}")
            
            # Check for permission error
            if "not permitted" in result.stderr or "not allowed" in result.stderr or "1002" in result.stderr:
                print("\n⚠️ PERMISSION ERROR DETECTED ⚠️")
                print("You need to allow your terminal app to control your computer.")
                print("Please follow these steps:")
                print("1. Open System Preferences/Settings")
                print("2. Go to Security & Privacy/Privacy > Accessibility")
                print("3. Click the lock icon to make changes")
                print("4. Add your terminal app (Terminal/iTerm) to the list")
                print("5. Restart your terminal and try again")
                print("\nAlternative: Use the manual input method below")
        else:
            print("AppleScript executed without errors")
    
    except Exception as e:
        print(f"AppleScript method failed: {e}")
    
    # Offer manual input as fallback
    print("\nIf automatic input failed, you can manually:")
    print(f"1. Switch to the {TARGET_APP_NAME} app window")
    print(f"2. Enter this code: {code}")
    print("3. Press Enter to submit")

def input_code_windows(code):
    """Input code on Windows systems"""
    print("Activating target application on Windows...")
    
    try:
        # Try to focus the target application window
        try:
            # Method 1: Using built-in Windows commands to focus the window
            # This tries to find and focus the window by title
            result = subprocess.run(
                ['powershell', '-Command', f'(New-Object -ComObject WScript.Shell).AppActivate("{TARGET_APP_NAME}")'], 
                capture_output=True, 
                text=True
            )
            if "True" in result.stdout:
                print("Successfully activated target window using PowerShell")
            else:
                # Try with just part of the window title (more likely to work)
                result = subprocess.run(
                    ['powershell', '-Command', f'(New-Object -ComObject WScript.Shell).AppActivate("{TARGET_APP_NAME.split()[0]}")'], 
                    capture_output=True, 
                    text=True
                )
                if "True" in result.stdout:
                    print("Successfully activated target window using partial title")
                else:
                    print(f"Could not activate {TARGET_APP_NAME} window with PowerShell")
                    print("Please manually focus the application window")
        except Exception as e:
            print(f"Error activating window: {e}")
            print("Please manually focus the application window")
        
        # Wait for window to gain focus
        time.sleep(1.5)
        
        # Method 1: Using PyAutoGUI directly
        print("\nMethod 1: Using PyAutoGUI directly...")
        try:
            # Press Tab to navigate to input field (adjust as needed for the app)
            pyautogui.press('tab')
            time.sleep(0.5)
            
            # Type the code
            pyautogui.typewrite(code)
            time.sleep(0.5)
            
            # Tab to the submit button
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.press('tab')
            time.sleep(0.5)
            
            # Press space to activate button
            pyautogui.press('space')
            
            print("PyAutoGUI method completed")
            return  # Success!
        except Exception as e:
            print(f"PyAutoGUI method failed: {e}")
        
        # Method 2: Using Windows keyboard shortcuts
        print("\nMethod 2: Using Windows keyboard simulation...")
        try:
            # Using keyboard shortcuts
            pyautogui.hotkey('alt', 'tab')  # Alt-Tab to ensure focus
            time.sleep(0.5)
            
            # Try to tab to input field and enter the code
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.typewrite(code)
            time.sleep(0.5)
            pyautogui.press('enter')
            
            print("Windows keyboard shortcut method completed")
        except Exception as e:
            print(f"Windows keyboard shortcut method failed: {e}")
            
        # Offer manual input as fallback
        print("\nIf automatic input failed, you can manually:")
        print(f"1. Switch to the {TARGET_APP_NAME} app window")
        print(f"2. Enter this code: {code}")
        print("3. Press Enter to submit")
        
    except Exception as e:
        print(f"Error in Windows input method: {e}")

def test_code_input():
    """Test the code input functionality with a sample code"""
    print("\n=== TESTING CODE INPUT FUNCTIONALITY ===")
    
    # Check if the target app is running (platform-specific)
    app_running = False
    
    if OPERATING_SYSTEM == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ['osascript', '-e', f'tell application "System Events" to count processes whose name is "{TARGET_APP_NAME}"'], 
                capture_output=True, text=True
            )
            app_running = result.stdout.strip() != "0"
        except Exception as e:
            print(f"Could not check if {TARGET_APP_NAME} is running: {e}")
    elif OPERATING_SYSTEM == "Windows":  # Windows
        try:
            result = subprocess.run(
                ['powershell', '-Command', f'Get-Process "{TARGET_APP_NAME}" -ErrorAction SilentlyContinue'], 
                capture_output=True, text=True
            )
            app_running = TARGET_APP_NAME in result.stdout
            
            # If not found, try partial name match
            if not app_running:
                result = subprocess.run(
                    ['powershell', '-Command', f'Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{TARGET_APP_NAME}*" }}'], 
                    capture_output=True, text=True
                )
                app_running = len(result.stdout.strip()) > 0
        except Exception as e:
            print(f"Could not check if {TARGET_APP_NAME} is running: {e}")
    
    if not app_running:
        print(f"WARNING: {TARGET_APP_NAME} does not appear to be running!")
        launch = input(f"Do you want to launch {TARGET_APP_NAME}? (y/n): ")
        if launch.lower() == 'y':
            if OPERATING_SYSTEM == "Darwin":  # macOS
                subprocess.run(['open', '-a', TARGET_APP_NAME])
            elif OPERATING_SYSTEM == "Windows":  # Windows
                try:
                    subprocess.Popen(f'start {TARGET_APP_NAME}', shell=True)
                except Exception:
                    print(f"Could not start {TARGET_APP_NAME}.")
                    print("Please launch it manually before continuing.")
            print(f"Launched {TARGET_APP_NAME}. Please position it properly on screen.")
            time.sleep(3)  # Give time for app to launch
        else:
            print(f"Please launch {TARGET_APP_NAME} manually before continuing.")
            time.sleep(2)
    
    # Get test code
    args = parse_args()
    if args.code:
        test_code = args.code
    else:
        test_code = input("Enter a code to test (or press Enter for 'TEST123'): ")
        if not test_code:
            test_code = "TEST123"
    
    print(f"\nWill attempt to input code '{test_code}' to {TARGET_APP_NAME} in 3 seconds...")
    print("Please make sure the app is ready and visible.")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    # Try to input the code
    input_code_to_app(test_code)
    
    # Ask for feedback
    result = input("\nDid the code input work correctly? (y/n): ")
    if result.lower() == 'y':
        print("Great! The code input functionality is working.")
    else:
        print("\nTroubleshooting suggestions:")
        if OPERATING_SYSTEM == "Darwin":  # macOS
            print("1. Make sure Fellou is running and has focus")
            print("2. Try clicking in the input field manually before running the test")
            print("3. Check if Fellou's UI layout has changed")
            print("4. You might need to adjust the AppleScript in the code to match Fellou's UI")
            print("5. Check you've granted accessibility permissions to Terminal/Python")
        elif OPERATING_SYSTEM == "Windows":  # Windows
            print("1. Make sure Fellou is running and has focus")
            print("2. Try clicking in the input field manually before running the test")
            print("3. Check if Fellou's UI layout has changed")
            print("4. You might need to adjust the tab sequence in the code to match Fellou's UI")
            print("5. Try running the script as administrator")
            print("6. Make sure the app window isn't minimized")

def main():
    """Main entry point"""
    args = parse_args()
    
    # Load user lists
    load_user_lists()
    
    # Check if we're just managing user lists
    list_management_args = args.ban or args.unban or args.whitelist or args.unwhitelist or args.list_filters
    if list_management_args:
        changes_made = manage_user_lists(args)
        if not args.test:  # If only managing lists without other actions, exit
            return
    
    # If in test mode, just test the code input functionality
    if args.test:
        test_code_input()
        return
    
    # Otherwise, start the monitor
    monitor_channel(poll_interval=args.interval)

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

def monitor_channel(poll_interval=5):
    """Monitor the Discord channel for new messages and invite codes"""
    print(f"Starting Discord channel monitor for: {CHANNEL_URL}")
    print(f"Polling interval: {poll_interval} seconds")
    print(f"Target application for codes: {TARGET_APP_NAME}")
    
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
                        # Try to get a fresh token
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

if __name__ == "__main__":
    main() 