
<div align=center>
  <img src="icon.png" alt="OMNX logo" width="full">
</div>

<div align="center">
  <h1 align="center">OMNX - A Rocket League Overlay </h1>
</div>

<div align=center>
  <a href="https://github.com/byEnok/rl-overlay/releases">Download Latest Release</a>
</div>

<a id="readme-top"></a>

<br>

  <details open>
  <summary><strong>Table of Contents</strong></summary>
    <!-- <ol style="list-style-position: outside; padding-left: 2%; inline-block; text-align: left;"> -->
    <!-- <ol style="display: table; margin: 0 auto; padding-left: 25px; text-align: left;"> -->
    <ol style="list-style-position: inside; padding-left: 2%; text-align: left;">
        <li><a href="#features">Features</a></li>
        <li><a href="#windows">Windows</a></li>
        <li><a href="#setup">Setup</a></li>
        <li><a href="#screenshots">Screenshots</a></li>
        <li><a href="#troubleshooting">Troubleshooting</a></li>
        <li><a href="#privacy">Privacy</a></li>
    </ol>
  </details>

  
<br>
<div align=center> 
  <h3>Track your wins, losses, win streaks and last 50 ranked matches with a lightweight, easy-to-use overlay</h3>
</div>

<br>


## **Features**
- **W/L Tracking** - Track wins and losses in **Ranked** 1v1, 2v2 and 3v3

- **Win streaks** - Keep track of your current streak

- **Match history** - View your 50 most recent ranked matches, including results, final scores and timestamps

- **Persistent Statistics** – Your match history and statistics are saved between application restarts

- **Custom Hotkeys** – Open Settings and Match History using configurable keyboard shortcuts

- **Movable Windows** – Position the overlay windows wherever you prefer with a simple drag and drop

- **Session Reset** – Reset your session statistics without deleting your match history

- **Local Storage** – Your data stays on your computer.
  
- **Quit from Session Window** – Close OMNX using the "X" button in the session window.

- **System Tray** – Quit OMNX directly from its system tray icon.

<br>

## **Windows**
 - Session - View your current W/L statistics and win streaks
 - Settings - Configure your launcher ID and hotkeys.
 - Match history - Browse your 50 most recent ranked matches.

<br>

# **Setup**

### **1. Configure Rocket League**

- Locate your Rocket League installation folder and open:
  - rocketleague\TAGame\Config\DefaultStatsAPI.ini

- Add or update these lines:
  - **PacketSendRate=1**
  - **Port=49123**

**Save the file** before exiting and don't launch Rocket League yet.

<br>

### **2. Configure Your Launcher & Player ID**

- Open the Settings window in OMNX and select the launcher you use to play Rocket League.
- Enter the corresponding player ID:
  - **Steam** – Your 17-digit Steam ID (e.g: 76561197960287930)
  - **Epic Games** – Your Epic Games Account ID (e.g: 3444634fab9a427ab453d4d232aad97e)

- In-game name (optional but recommended) – Enter your current Rocket League display name to help OMNX identify you more reliably.

**Remember to save your settings!**

<br>

**IMPORTANT!**

Complete Steps 1 and 2 before launching Rocket League. Make sure you've saved both the configuration file and your OMNX settings.

<br>

### **3. Configure Display Mode**

- You can now launch Rocket League.

- Set Rocket League's display mode to Borderless so the overlay can appear over the game.

- If you prefer exclusive fullscreen, you can keep that and just place the overlay on a Second Monitor.

Once everything is configured, launch Rocket League and OMNX in no particular order.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<br>

# **Screenshots**
<table align="center" >
  <tr>
    <td align="center" valign="top">
      <h3>Session</h3>
      <img src="screenshots/session.jpg" alt="OMNX Session" width="300">
      <h3>Settings</h3>
      <img src="screenshots/settings.jpg" alt="OMNX Settings" width="300">
    </td>
  <td width="100"></td>
    <td align="center" valign="top">
      <h3>Match History</h3>
      <img src="screenshots/match_history.jpg" alt="OMNX Match History" width="172">
    </td>
  </tr>
</table>


<img src="screenshots/all_windows_in_game_anon.jpg" alt="OMNX in game preview" width="full">

<p align="left">(<a href="#readme-top">back to top</a>)</p>

<br>

<a href="https://github.com/byEnok/rl-overlay/releases">Download Latest Release</a>

# **Troubleshooting**

### **If OMNX does not track your matches:**
- Verify that the **correct** launcher ID is configured.

- Check that DefaultStatsAPI.ini contains the required settings.

- Restart Rocket League after changing the configuration file.

- Make sure you are playing **Ranked** 1v1, 2v2, or 3v3.

<br>

# **Privacy**

### OMNX is designed to run locally.
 - No data transmission: Your match history and statistics are never uploaded or sent to external servers.
 - Local data storage: Match history, statistics, and application settings are stored on your computer and persist between restarts.
 - On Windows, your data is stored in C:\Users\<username>\AppData\Local\OMNX\overlay.db.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
