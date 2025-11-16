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
from openai import OpenAI

app = Flask(__name__)

# --- CRITICAL FIX: Load all credentials from environment variables ---
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def send_email(to_email, subject, html_body, attachments):
    """Sends an HTML email with optional attachments using environment variables."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("ERROR: Email credentials (EMAIL_SENDER/EMAIL_PASSWORD) not set in environment variables.")
        # Raise an exception or return False if credentials are missing
        raise ValueError("Email credentials not configured.")
        
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))
    
    for file_path in attachments:
        try:
            with open(file_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
            msg.attach(part)
        except FileNotFoundError:
            print(f"Warning: Attachment file not found at {file_path}")
            continue
            
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        print("ERROR: SMTP Authentication Failed. Check App Password (EMAIL_PASSWORD).")
        raise # Re-raise to be caught by the /analyze route's main error handler
    except Exception as e:
        print(f"ERROR during email sending: {e}")
        raise # Re-raise to be caught by the /analyze route's main error handler


def generate_summary_with_ai(username, mood_counts, dominant_mood, suggestions):
    """Generate a summarized, empathetic mood report using Generative AI."""
    try:
        if not client.api_key:
             return "(AI summary unavailable: OPENAI_API_KEY not set)"

        prompt = f"""
        You are a compassionate AI health assistant summarizing mood data for an elder care report.

        Elder's Name: {username}
        Mood distribution: {json.dumps(mood_counts, indent=2)}
        Dominant mood: {dominant_mood}
        Observations and suggestions: {json.dumps(suggestions, indent=2)}

        Please write a warm, concise summary (in about 100-150 words) that:
        - Summarizes how the elder has been feeling.
        - Highlights the dominant mood.
        - Gives 2–3 actionable recommendations for their caregiver.
        - Keeps the tone supportive and easy to understand.
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an empathetic elder-care assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OPENAI API Error: {e}") 
        return f"(AI summary unavailable due to API error.)"

@app.route("/analyze", methods=["POST"])
def analyze():
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
        username = data.get("user_name", "Your loved one")

        df_all = pd.DataFrame(all_logs)
        if "mood" not in df_all.columns:
            return jsonify({"status": "error", "message": "Missing mood column"}), 400

        # Mood statistics (all logs)
        mood_counts = Counter(df_all["mood"])
        total_moods = sum(mood_counts.values())
        percentages = {m: (c / total_moods) * 100 for m, c in mood_counts.items()}
        dominant_mood = max(mood_counts, key=mood_counts.get)

        # Prepare survey-only dataframe for clustering (requires full features)
        feature_cols = ["sleep", "water", "exercise", "pain", "energy", "mood"]
        df_survey = pd.DataFrame(survey_logs)
        do_cluster = all(col in df_survey.columns for col in feature_cols) and not df_survey.empty

        suggestions = []
        if do_cluster:
            # Clustering logic
            df_survey_feat = df_survey[feature_cols].copy() 
            encoders = {}
            for col in df_survey_feat.columns:
                le = LabelEncoder()
                df_survey_feat[col] = le.fit_transform(df_survey_feat[col].astype(str))
                encoders[col] = le

            df_feat = df_survey_feat.drop(columns=["mood"])
            
            try:
                kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
                df_survey_feat["cluster"] = kmeans.fit_predict(df_feat)
                df_survey_feat["mood_lbl"] = df_survey_feat["mood"]
                cluster_mean = df_survey_feat.groupby("cluster").mean()
                bad, good = sorted(cluster_mean.index, key=lambda i: cluster_mean.loc[i]["mood_lbl"])

                for col in df_feat.columns:
                    bad_v = cluster_mean.loc[bad][col]
                    good_v = cluster_mean.loc[good][col]
                    if abs(good_v - bad_v) >= 0.5:
                        try:
                            to_v = encoders[col].inverse_transform([int(round(good_v))])[0]
                        except ValueError:
                            to_v = "Optimal Level"
                            
                        msg_map = {
                            "sleep": f"• They feel better on <b>{to_v.lower()}</b> sleep days.",
                            "water": "• Higher water intake correlates with better emotional stability.",
                            "exercise": "• Consistent activity improves mood and energy levels.",
                            "pain": "• Monitor and manage pain; lower pain predicts a brighter mood.",
                            "energy": "• Higher energy levels are strongly linked to positive moods."
                        }
                        suggestions.append(msg_map.get(col, f"• Improving <b>{col}</b> may help."))
            except Exception as e:
                print(f"Clustering Analysis Error: {e}")
                suggestions.append("• Behavioral analysis failed due to data complexity.")


        if not suggestions:
            suggestions.append("• No immediate behavioral factors correlated with mood swings this week. Continue with current routines.")

        # Mood chart generation
        os.makedirs("output", exist_ok=True)
        fig, ax = plt.subplots(figsize=(9, 5))
        
        mood_colors = {
            'Happy': '#4CAF50', 'Calm': '#2196F3', 'Anxious': '#FF9800', 
            'Neutral': '#9E9E9E', 'Sad': '#F44336'
        }
        bar_colors = [mood_colors.get(m, '#607D8B') for m in mood_counts.keys()]

        bars = ax.bar(mood_counts.keys(), mood_counts.values(), color=bar_colors, edgecolor="black")
        
        if dominant_mood in mood_counts:
            dominant_idx = list(mood_counts.keys()).index(dominant_mood)
            bars[dominant_idx].set_color('#ff8c42') 
            bars[dominant_idx].set_edgecolor('red')

        for idx, bar in enumerate(bars):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    f"{percentages[list(mood_counts.keys())[idx]]:.1f}%",
                    ha="center", va="bottom", fontsize=11, fontweight="bold")
        ax.set_title(f"🧠 Mood Trend for {username}", fontsize=18, color="teal")
        ax.set_ylabel("Count")
        ax.set_ylim(0, max(mood_counts.values()) + 2)
        sns.despine()
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        chart_path = "output/mood_chart.png"
        plt.tight_layout()
        plt.savefig(chart_path, dpi=300)
        plt.close()
        
        # Generate AI Summary
        ai_summary = generate_summary_with_ai(username, mood_counts, dominant_mood, suggestions)

        # Email body
        summary_html = "".join(f"<li style='color:{mood_colors.get(m, '#000')};'><b>{m}</b>: {mood_counts[m]} ({percentages[m]:.1f}%)</li>" for m in mood_counts)
        sug_html = "".join(f"<li>{s}</li>" for s in suggestions)
        
        email_body = f"""
        <html><body style="font-family: Arial, sans-serif; line-height: 1.6; background-color: #f4f7f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); padding: 20px;">
                <h2 style="color: #00796b; border-bottom: 2px solid #e0f2f1; padding-bottom: 10px;">🧓 Weekly Mood Report for {username}</h2>
                
                <div style="background-color: #e0f7fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #00796b; margin-top: 0;">🧠 AI Summary:</h3>
                    <p>{ai_summary}</p>
                </div>

                <h3 style="color: #00796b;">📊 Mood Distribution:</h3>
                <ul style="list-style: none; padding: 0;">{summary_html}</ul>

                <h3 style="color: #00796b;">💡 Detailed Suggestions:</h3>
                <ul style="padding-left: 20px;">{sug_html}</ul>
                
                <p style="text-align: center; margin-top: 25px; font-style: italic; color: #666;">
                    See attached chart for visual trends.
                </p>

                <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #999;">
                    &mdash; Elder Mood Mirror &mdash;
                </div>
            </div>
        </body></html>
        """

        if email:
            send_email(email, f"AI Mood Report for {username} 📊", email_body, [chart_path])
        if clinic_email and "@" in clinic_email:
            send_email(clinic_email, f"[Clinic] AI Report – {username}", email_body, [chart_path])

        return jsonify({"status": "success", "dominant_mood": dominant_mood,
                        "suggestions": suggestions, "ai_summary": ai_summary, "mood_chart": "/output/mood_chart.png"}), 200

    except Exception as e:
        print(f"An unexpected error occurred: {e}") 
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
