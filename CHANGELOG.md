# Changelog

All notable changes to the **Gheychee** project will be documented in this file.

## [v2.0.0] - 2025-12-15

### 🚀 Added
-   **Multiple Tiers**: Introduced `Free`, `Premium`, and `Super` tiers with specific platform permissions.
-   **Rate Limiting**: Enforced daily download limits per tier (3/5/20).
-   **Platform Verification**: Logic to allow/block downloads based on the source URL (Twitter, LinkedIn, Instagram, TikTok).
-   **Firebase Integration**: Added `firebase_config.py` to handle Firestore connection for user management and logging.
-   **Admin Dashboard**: Created `admin_dashboard.py` using Streamlit to visualize stats (Active Users, Success Rate, Platform Usage) and manage user tiers.
-   **Logging**: All requests (success, failed, blocked) are now logged to Firestore.

### 🔄 Changed
-   Refactored `handle_link` to use middleware-style permission checks.
-   Updated `/start` message to display tier information.

## [v1.0.0] - 2025-12-14

### 🎉 Initial Release
-   Basic video download functionality using `yt-dlp`.
-   Simple Telegram bot responding to links.
-   Environment variable support for Token.
