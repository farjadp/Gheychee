# Gheychee Bot ✂️

**Gheychee** (قیچی) is a smart Telegram bot designed to download videos from social media platforms like Twitter (X), LinkedIn, Instagram, and TikTok. It features a tiered user system, rate limiting, and a comprehensive admin dashboard.

## 🌟 Features

-   **Video Downloader**: Downloads videos directly from links.
-   **User Tiers**:
    -   **Free**: 3 downloads/day (Twitter only).
    -   **Premium**: 5 downloads/day (Twitter + LinkedIn).
    -   **Super**: 20 downloads/day (All Platforms: Twitter, LinkedIn, Instagram, TikTok).
-   **Admin Dashboard**: A web-based interface (using Streamlit) to monitor users, change tiers, and view analytics.
-   **Firebase Integration**: Stores user data and request logs in Google Firestore.
-   **Rate Limiting**: Automatically blocks requests exceeding daily limits.

## 🛠 Installation

### Prerequisites
-   Python 3.9+
-   A Telegram Bot Token (from @BotFather)
-   Google Cloud Project with Firestore enabled
-   Firebase Service Account JSON key

### Setup Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/farjadp/Gheychee.git
    cd Gheychee
    ```

2.  **Create Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Secrets**
    -   Create a `.env` file:
        ```bash
        TELEGRAM_TOKEN=your_telegram_bot_token_here
        ```
    -   Place your Firebase key as `service_account.json` in the root folder.

5.  **Run the Bot**
    ```bash
    python3 bot.py
    ```

## 📊 Admin Dashboard

To view the admin panel and analytics:

```bash
streamlit run admin_dashboard.py
```
Access the dashboard in your browser (default port 8501).

## 🗄 Project Structure

-   `bot.py`: Main bot logic (handlers, platform checks).
-   `firebase_config.py`: Database connection and helper functions.
-   `admin_dashboard.py`: Streamlit application for admin stats.
-   `requirements.txt`: Python dependencies.
