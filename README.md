# 👵👴 Elder Mood Mirror Application (EMMA)

**An AI-Powered Well-being Monitoring System for Elderly Care.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Flutter](https://img.shields.io/badge/Flutter-Frontend-02569B?logo=flutter)](https://flutter.dev/)
[![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/AI-OpenAI%20API-41295D?logo=openai)](https://openai.com/)

---

## ✨ Overview

**Elder Mood Mirror (EMMA)** is an innovative mobile application designed to proactively monitor, analyze, and improve the emotional well-being of elderly individuals. By combining **daily subjective input (surveys)** with **objective data (facial analysis)**, EMMA provides caregivers with timely, AI-generated insights and actionable recommendations to ensure better emotional health management.

### The Problem We Solve
Aging individuals, particularly those with reduced mobility, often struggle to consistently communicate their mood or symptoms, leading to delayed interventions for stress, depression, or chronic pain. EMMA bridges this communication gap using data and AI.

---

## 🚀 Key Features

* **👤 Personalized Profile Setup:** Quick setup capturing essential user details (age, medical conditions) to tailor the daily experience.
* **📋 Contextual Daily Survey:** Generates streamlined questions based on the user's defined medical conditions (e.g., Bedridden vs. Mobile).
* **📷 Facial Expression Analysis (Planned):** Uses the device camera to auto-detect and log mood, providing objective data points for analysis.
* **🤖 AI-Powered Weekly Insights:** Generates a professional, empathetic summary and actionable recommendations (based on K-Means clustering and OpenAI's GPT-4o-mini) delivered directly to caregivers via email.
* **💬 Motivational Quotes:** Provides daily positive reinforcement and emotional support directly on the start screen.
* **🔒 Secure Credential Management:** Flask backend uses environment variables for all API keys and emails.

---

## 🖼️ Prototype & Screenshots

### Figma Prototype Link
🔗 https://emma.figma.site/

| Main Dashboard | Daily Survey | Mood Detection | Analysis Summary | Email Report (Popped) |
| :---: | :---: | :---: | :---: | :---: |
| ![Main Dashboard](main%20dashboard.png) | ![Survey Screen](survey%20screen.png) | ![Mood Detection](mood%20detection%20screen.png) | ![Analysis Summary](mood%20analysis%20summary.png) | ![Email Report](mood%20report%20via%20mail.png) |
![Daily exercise]("D:\AISHH\nxtwaveXopenai\daily execise list .jpg") | [Daily quotes]("D:\AISHH\nxtwaveXopenai\daily quotes pic.jpg") | [exercises]("D:\AISHH\nxtwaveXopenai\exercises pic.jpg")

---

## 📱 App Demo

### 🎥 Video Walkthrough
![App Demo](https://youtube.com/shorts/xYZmQgXaLzU?feature=share)

---

## ⚙️ System Architecture

EMMA uses a robust, two-tier architecture designed for scalability and real-time processing.

### Architecture Diagram
![System Architecture](WhatsApp%20Image%202025-09-10%20at%2020.54.41_2b8d6c60.jpg)

**Workflow Summary:**
1.  **Frontend (Flutter):** Captures daily survey and camera mood data.
2.  **API Gateway (Flask):** Receives and validates JSON logs.
3.  **Data Analysis:** Python/Pandas aggregates weekly logs (7 days).
4.  **Clustering & Insight:** K-Means clustering identifies behavioral correlates (e.g., pain, sleep) of good vs. bad mood days.
5.  **Generative AI (OpenAI):** GPT-4o-mini synthesizes the data and clustering insights into a compassionate, actionable summary.
6.  **Reporting:** An enhanced HTML email report is generated and sent to the caregiver/clinic.
7.  **Future:** Firebase (FCM) is planned for real-time notifications and reminders.

### Tech Stack Breakdown

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Mobile App** | **Flutter (Dart)** | Cross-platform frontend for interactive surveys and camera input. |
| **Backend API** | **Flask (Python)** | Lightweight REST API for data ingestion and processing. |
| **Data Science** | **Pandas, scikit-learn** | Data cleaning, aggregation, and K-Means clustering. |
| **Intelligence** | **OpenAI API (GPT-4o-mini)** | Generative AI for emotional, compassionate report summaries. |
| **State/Data** | **SharedPreferences, JSON** | Local storage and current data structure (planned upgrade to SQLite/NoSQL). |

---

## 🛠️ Installation & Setup

### Prerequisites

Ensure you have the following installed:
* Flutter SDK
* Python 3.8+
* Android SDK **36 or higher** (required by `camera_android` plugin).

### 1. Clone Repository & Setup Backend

```bash
git clone https://github.com/<yourusername>/ElderMoodMirror.git
cd ElderMoodMirror

# Create and activate Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

### 2. Configure Environment Variables ⚠️

For security, the application requires credentials set as environment variables.

#### Linux/macOS:
```bash
export OPENAI_API_KEY='your_openai_key'
export EMAIL_SENDER='yourappemail@gmail.com'
export EMAIL_PASSWORD='your_gmail_app_password'
```

#### Windows:
```bash
set OPENAI_API_KEY='your_openai_key'
set EMAIL_SENDER='yourappemail@gmail.com'
set EMAIL_PASSWORD='your_gmail_app_password'
```

---

### 3. Run the Backend Server

```bash
python app.py
```

(If running on Android Emulator, use **10.0.2.2** as the base URL in Flutter.)

---

### 4. Run the Flutter Frontend

```bash
cd frontend
flutter pub get
flutter run
```

---

## 📈 Future Enhancements

* **Voice Accessibility** for survey interaction  
* **Wearable / IoT Integration** (heart rate, sleep tracking)  
* **Caregiver Dashboard** (Web)  
* **Real-time Notifications** via Firebase Cloud Messaging  

---

## ⚖️ License  
This project is licensed under the **MIT License** — see the `LICENSE` file for details.
