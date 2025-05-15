# Discord Channel Monitor for Fellou Invite Codes

This tool monitors a specific Discord channel for messages and automatically extracts invite codes to enter them into another application.

## Demo Video

https://github.com/user-attachments/assets/7ead73e7-b790-4fe3-a5ae-cae17bcada77


## Features

- Uses Discord API to authenticate and fetch messages directly
- Monitors a specific Discord channel for new messages
- Automatically extracts invite codes that match a pattern
- Inputs found codes into another application (Fellou)
- Saves authentication token for future sessions
- Filters messages based on user whitelist and ban list
- Robust connection handling with automatic retries for network issues

## Getting Started for Non-Developers

If you're not familiar with programming, follow these steps to get started:

1. **Install Python**:

   - Download and install Python from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Set up macOS permissions**:

   - Go to System Preferences/Settings > Security & Privacy/Privacy > Accessibility
   - Add Terminal.app to the list of apps that can control your computer

3. **Open Terminal.app**:

   - Search for "Terminal" in Spotlight (Cmd+Space)

4. **Install Homebrew**:

   - Copy and paste this command:
     ```
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```
   - Enter your Mac password when prompted (you won't see characters as you type)
   - Press Enter

5. **Set up Homebrew in your path**:

   - Copy and paste these commands:
     ```
     echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
     source ~/.zshrc
     ```

6. **Install pipx**:

   - Copy and paste these commands:
     ```
     brew install pipx
     pipx ensurepath
     source ~/.zshrc
     pipx --version
     ```
   - The last command should show the pipx version

7. **Install Poetry**:

   - Copy and paste these commands:
     ```
     pipx install poetry
     pipx upgrade poetry
     poetry --version
     ```
   - The last command should show the poetry version

8. **Download and set up the project**:

   - Download and unzip the project archive
   - In Terminal, type `cd ` (with a space after cd)
   - Drag and drop the project folder into Terminal
   - Press Enter
   - Run this command:
     ```
     poetry install
     ```

9. **Check for whitelist**:

   - Check for whilte list accounts for which we well watch for new accounts
   - By default it is list of admins

   ```
   poetry run python -m src.discord_api_client --list-filters
   ```

10. **Test the application**:

- Open Fellou application
- Position both Fellou and Terminal so you can see both
- Run this command:
  ```
  poetry run python -m src.discord_api_client --test --code M1C0DE
  ```
- Verify that the code is automatically entered in Fellou
- Type 'y' in Terminal and press Enter

11. **Run the application**:

    - Make sure you're already logged into Discord desktop app on your Mac
    - Run this command:
      ```bash
      poetry run python -m src.discord_api_client
      ```
    - Enter your Discord email and password when prompted

12. **DO NOT SHARE** your folder to another user, beacause it stores sensetive info about your discord token. Just send this repository

13. Work well on MacOS, not tested on windows.

On first run, you'll be prompted to log in with your Discord credentials. The authentication token will be saved for future sessions.

## Disclaimer and License

**FOR EDUCATIONAL PURPOSES ONLY**

This software is provided strictly for educational and personal use purposes only. By using this software, you agree to the following:

1. This software is meant to demonstrate technical concepts and automate personal tasks. It is not intended for commercial use, mass distribution, or any activity that violates Discord's Terms of Service.

2. The user assumes full responsibility for how they use this software. The creator(s) of this software cannot be held liable for any misuse, violations of terms of service, or any damages that may result from using this software.

3. Automated interactions with Discord may potentially violate Discord's Terms of Service. Use of this software to interact with Discord is at your own risk.

4. This software comes with no warranty, express or implied. It is provided "AS IS" without warranty of any kind, either expressed or implied, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose.

5. The creator(s) of this software shall not be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, procurement of substitute goods or services; loss of use, data, or profits; or business interruption) however caused and on any theory of liability, whether in contract, strict liability, or tort (including negligence or otherwise) arising in any way out of the use of this software, even if advised of the possibility of such damage.

By downloading, installing, or using this software, you acknowledge that you have read this disclaimer, understand its contents, and agree to be bound by its terms.

## Professional Support & Development

Need additional functionality or facing technical issues? The developer offers professional services:

- **Custom Development**: Tailored solutions for Telegram, Discord, or other platform automation
- **Integration Services**: Connect your existing systems with messaging platforms
- **Technical Support**: Troubleshooting and optimization for your specific needs
- **Training**: Learn how to extend this tool for your specific use case

### Contact

For professional inquiries or custom development requests, please reach out directly to the developer.

### Support This Project

If you find this tool useful, consider supporting its continued development:

- **Cryptocurrency**:

  - SOL: `AR37Ja9QMZyHKp4rZE9bfB9eEjpqQXfrJrpTQqNGWjRy`
  - SUI: `0x68da16b20707ed4d6a173200a2f1ae1bc89bbe432af5bd21a8747431e6cda136`

Your support helps maintain this tool and develop new features.

The script will then:

1. Monitor the specified Discord channel
2. Display new messages in real-time
3. Extract any invite codes matching the pattern
4. Automatically input these codes into the target application

### User Filtering

The script now supports filtering users whose messages will be processed:

#### Managing the Ban List

Users on the ban list will always be ignored:

```bash
# Add a user to the ban list
python src/discord_api_client.py --ban USER_ID

# Remove a user from the ban list
python src/discord_api_client.py --unban USER_ID
```

#### Managing the Whitelist

If the whitelist is not empty, only messages from whitelisted users will be processed:

```bash
# Add a user to the whitelist
python src/discord_api_client.py --whitelist USER_ID

# Remove a user from the whitelist
python src/discord_api_client.py --unwhitelist USER_ID
```

#### View Current Filters

To see the current ban list and whitelist:

```bash
python src/discord_api_client.py --list-filters
```

#### How Filtering Works

1. If the whitelist is empty, messages from all users are processed (except banned users)
2. If the whitelist has entries, only messages from those users are processed
3. Messages from banned users are always ignored
4. Your user ID is automatically added to the whitelist when you run the script

### Manual Code Entry Version

If you're having permission issues, there's also a manual version:

```bash
python src/manual_code_entry.py
```

This version will display codes but requires you to manually enter them into the application. It supports the same user filtering options.

## Troubleshooting Permission Errors

If you see errors like "Sending keystrokes is not permitted/allowed (1002)" (or "Отправка нажатий клавиш для «osascript» не разрешена. (1002)"), follow these steps:

1. Open System Preferences/Settings
2. Go to Security & Privacy/Privacy > Accessibility
3. Click the lock icon to make changes (enter your password if prompted)
4. Make sure your terminal app is checked/enabled in the list
5. If your terminal app isn't in the list, click the "+" button and add it
6. You may need to restart your terminal or computer for changes to take effect

If permission issues persist, the script will still display the invite codes in the terminal, allowing you to manually enter them into the application.

## Connection Error Handling

The script now includes robust connection error handling:

- Automatically retries failed API requests with exponential backoff
- Handles temporary network issues and API outages
- Increases wait time between retries for persistent issues
- Automatically refreshes the authentication token if needed

## How the Authentication Works

This script uses your Discord credentials to obtain an authentication token through the Discord API. Note that programmatic login is against Discord's Terms of Service, so use this at your own risk.

## Files in this Project

- `src/discord_api_client.py` - The main script that uses the Discord API to fetch messages and auto-inputs codes
- `src/manual_code_entry.py` - A version that displays codes but requires manual input (for permission issues)
- `discord_token.txt` - Generated file that stores your Discord authentication token
- `user_filters.json` - Stores ban list and whitelist user IDs

## Troubleshooting

If you encounter authentication issues:

1. Delete the `discord_token.txt` file to force re-authentication
2. Ensure you're entering the correct Discord credentials
3. If you have 2FA enabled, you'll need to enter your 2FA code when prompted

If you encounter connection issues:

1. Check your internet connection
2. The script will automatically retry with increasing delays
3. After multiple failures, it will refresh your Discord token

## Security Note

The script saves your Discord token to a local file. Ensure this file is kept secure and not shared with others.
