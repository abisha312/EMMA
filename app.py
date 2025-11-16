from flask import Flask, request, jsonify
import os, smtplib, json
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import KMeans
import seaborn as sns
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Load credentials from environment variables for security
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # This must be the App Password

app = Flask(__name__)

def send_email(to_email, subject, html_body, attachments):
    """Sends an HTML email with optional attachments using credentials from env vars."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("ERROR: Email credentials not set in environment variables.")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    
    # Attach HTML body
    msg.attach(MIMEText(html_body, "html"))
    
    # Attach files
    for file_path in attachments:
        try:
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
            msg.attach(part)
        except FileNotFoundError:
            print(f"Warning: Attachment file not found at {file_path}")
            continue

    # Send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError:
        print("ERROR: SMTP Authentication Failed. Check EMAIL_PASSWORD (App Password).")
        return False
    except Exception as e:
        print(f"ERROR during email sending: {e}")
        return False

@app.route("/analyze", methods=["POST"])
def analyze():
    """Receives JSON logs, performs mood analysis, generates a chart, and sends an email report."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON body"}), 400

        survey_logs = data.get("daily_logs", [])
        camera_logs = data.get("camera_moods", [])
        all_logs = survey_logs + camera_logs
        if not all_logs:
            return jsonify({"status": "error", "message": "No mood data"}), 400

        email = data.get("guardian_email", "")
        clinic_email = data.get("clinic_email", "")
        username = data.get("user_name", "User") 

        df_all = pd.DataFrame(all_logs)
        if "mood" not in df_all.columns:
            return jsonify({"status": "error", "message": "Missing 'mood' column in logs"}), 400

        # --- Mood statistics (all logs) ---
        mood_counts = Counter(df_all["mood"])
        total_moods = sum(mood_counts.values())
        percentages = {m: (c / total_moods) * 100 for m, c in mood_counts.items()}
        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else "Neutral"

        # --- Mood-specific coloring for the UI and email ---
        mood_color = {
            'Happy': '#4CAF50',    # Green
            'Calm': '#2196F3',     # Blue
            'Anxious': '#FF9800',  # Orange
            'Neutral': '#9E9E9E',  # Grey
            'Sad': '#F44336'       # Red
        }.get(dominant_mood, '#607D8B') # Default to slate color

        # --- K-Means Clustering for Suggestions (Survey Data Only) ---
        feature_cols = ["sleep", "water", "exercise", "pain", "energy", "mood"]
        df_survey = pd.DataFrame(survey_logs)
        suggestions = []

        # Only proceed with clustering if survey data is available and complete
        do_cluster = all(col in df_survey.columns for col in feature_cols) and not df_survey.empty

        if do_cluster:
            try:
                # 1. Prepare data and encode categorical features
                df_survey = df_survey[feature_cols].copy() 
                
                # Apply LabelEncoder to all relevant columns (including 'mood')
                encoders = {}
                for col in df_survey.columns:
                    le = LabelEncoder()
                    df_survey[col] = le.fit_transform(df_survey[col].astype(str))
                    encoders[col] = le

                # 2. Separate features (X) from the target (mood) for clustering
                df_feat = df_survey.drop(columns=["mood"])

                # 3. Perform K-Means Clustering
                # We use n_init=10 explicitly to avoid the default warning
                kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
                df_survey["cluster"] = kmeans.fit_predict(df_feat)

                # 4. Analyze cluster means
                df_survey["mood_lbl"] = df_survey["mood"]
                cluster_mean = df_survey.groupby("cluster").mean()

                # Determine 'bad' (lower mean encoded mood) and 'good' clusters
                bad, good = sorted(cluster_mean.index, key=lambda i: cluster_mean.loc[i]["mood_lbl"])

                # 5. Compare feature means between clusters to find correlations
                for col in feature_cols[:-1]: # Iterate over actual feature columns, excluding 'mood'
                    bad_v = cluster_mean.loc[bad].get(col)
                    good_v = cluster_mean.loc[good].get(col)

                    # Check for a meaningful difference (e.g., encoded difference of 0.5 or more)
                    if bad_v is not None and good_v is not None and abs(good_v - bad_v) >= 0.5:
                        msg_map = {
                            "sleep": "Focus on **consistent sleep quality** as it shows a strong correlation with positive mood states.",
                            "water": "Encourage adequate **daily hydration**; emotional stability increases on days with higher intake.",
                            "exercise": "Introduce light **daily activity/stretching**; physical movement boosts energy and mood.",
                            "pain": "Monitor and manage **pain levels** closely, as lower pain predicts a brighter mood outlook.",
                            "energy": "Higher **energy** levels typically accompany positive mood. Check for daytime energy dips.",
                        }
                        suggestions.append(msg_map.get(col, f"Improvement in **{col.capitalize()}** shows potential for better well-being."))
            except Exception as e:
                print(f"Clustering Error: {e}")
                suggestions.append("Could not perform detailed behavioral analysis this week. Data complexity may be a factor.")


        if not suggestions:
            suggestions.append("No immediate behavioral factors correlated with mood swings this week. Continue with current routines.")


        # --- Mood Chart Generation ---
        os.makedirs("output", exist_ok=True)
        fig, ax = plt.subplots(figsize=(9, 5))
        
        # Plotting logic
        colors = sns.color_palette("viridis", len(mood_counts))
        mood_names = list(mood_counts.keys())
        mood_values = list(mood_counts.values())
        
        bars = ax.bar(mood_names, mood_values, color=colors, edgecolor="black")

        # Color the dominant mood
        if dominant_mood in mood_names:
            dominant_idx = mood_names.index(dominant_mood)
            bars[dominant_idx].set_color(mood_color) # Use specific color for dominant mood

        # Add percentage labels
        for idx, bar in enumerate(bars):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    f"{percentages[mood_names[idx]]:.1f}%",
                    ha="center", va="bottom", fontsize=11, fontweight="bold")
                    
        ax.set_title(f"🧠 Mood Trend for {username}", fontsize=18, color="#00796b") # Teal color
        ax.set_ylabel("Count")
        ax.set_ylim(0, max(mood_values) + 2)
        sns.despine()
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        chart_path = "output/mood_chart.png"
        plt.tight_layout()
        plt.savefig(chart_path, dpi=300)
        plt.close()


        # -----------------------------------------------------
        # --- AI REPORT HTML BODY GENERATION ---
        # -----------------------------------------------------

        # 1. Generate the Mood Breakdown List (List with colors)
        summary_html = ""
        for m in sorted(mood_counts.keys(), key=lambda k: percentages[k], reverse=True):
            p = percentages[m]
            c = mood_counts[m]
            item_color = '#000000' if m == dominant_mood else '#444444'
            summary_html += f"""
            <li style="color: {item_color}; font-weight: {('bold' if m == dominant_mood else 'normal')}; padding: 3px 0; display: flex; justify-content: space-between; align-items: center;">
                <span style="display: inline-block; width: 100px;">{m}:</span> 
                <span>{c} times</span>
                <span style="font-weight: bold;">({p:.1f}%)</span>
            </li>
            """

        # 2. Generate the Actionable Suggestions (Card/Box Style)
        sug_html = ""
        for s in suggestions:
            sug_html += f"""
            <div style="
                background-color: #F0F8FF; /* Light Blue Background */
                border-left: 5px solid #00796b; /* Teal border */
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                font-size: 15px;
                line-height: 1.4;
            ">
                <span style="font-weight: bold; color: #00796b;">&#9889; AI Recommendation:</span><br>
                {s}
            </div>
            """

        email_body = f"""
        <html><body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                
                <div style="background-color: #00796b; padding: 20px; color: white;">
                    <h2 style="margin: 0; font-size: 24px;">📊 Weekly Mood Report for {username}</h2>
                </div>

                <div style="padding: 20px;">
                    <p style="font-size: 16px; color: #333;">
                        Here's an analytical summary of {username}'s well-being over the past week:
                    </p>

                    <div style="background-color: {mood_color}; color: white; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                        <span style="font-size: 14px; display: block;">🌟 Dominant Mood Detected</span>
                        <b style="font-size: 28px; display: block;">{dominant_mood}</b>
                        <span style="font-size: 14px;">(Accounted for {percentages.get(dominant_mood, 0.0):.1f}% of all entries)</span>
                    </div>

                    <h3 style="color: #00796b; border-bottom: 2px solid #e0f2f1; padding-bottom: 5px;">🧠 Mood Distribution</h3>
                    <ul style="list-style: none; padding: 0; margin: 0;">{summary_html}</ul>

                    <h3 style="color: #00796b; border-bottom: 2px solid #e0f2f1; padding: 20px 0 5px 0;">💡 Correlated Insights & Recommendations</h3>
                    {sug_html}
                    
                    <p style="text-align: center; margin-top: 30px; font-style: italic; color: #666;">
                        See attached chart for a visual summary of the distribution.
                    </p>
                </div>

                <div style="background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #e0e0e0;">
                    &mdash; Elder Mood Mirror &mdash;
                </div>
            </div>
        </body></html>
        """

        # --- Email Sending ---
        if email:
            send_email(email, f"AI-Driven Well-being Report for {username} 📊", email_body, [chart_path])
        if clinic_email and "@" in clinic_email:
            send_email(clinic_email, f"[Clinic] AI Report – {username}", email_body, [chart_path])

        return jsonify({"status": "success", "dominant_mood": dominant_mood,
                        "suggestions": suggestions, "mood_chart": "/output/mood_chart.png"}), 200

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # NOTE: When deploying to Render, Gunicorn (or a similar WSGI server) will run this app.
    # The debug settings below are only for local development.
    app.run(debug=True, host="0.0.0.0", port=5000)
