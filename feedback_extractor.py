"""
Feedback extractor - Run this after using the HTML file to process feedback
"""
import json
import os

def extract_feedback_from_browser():
    """
    Instructions for extracting feedback from browser localStorage
    """
    # Use generic Downloads folder
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    feedback_file = os.path.join(downloads_folder, "feedback.json")
    
    print("🔍 Feedback Extraction Instructions:")
    print("=" * 50)
    print("1. Open the generated_text.html file in your browser")
    print("2. Complete your vocabulary review and submit feedback")
    print("3. Open browser developer tools (F12)")
    print("4. Go to Console tab")
    print("5. Copy and paste this command:")
    print()
    print("   const feedback = localStorage.getItem('vocabularyFeedback');")
    print("   if (feedback) {")
    print("       const blob = new Blob([feedback], {type: 'application/json'});")
    print("       const url = URL.createObjectURL(blob);")
    print("       const a = document.createElement('a');")
    print("       a.href = url;")
    print("       a.download = 'feedback.json';")
    print("       a.click();")
    print("       console.log('Feedback downloaded!');")
    print("   } else {")
    print("       console.log('No feedback found in localStorage');")
    print("   }")
    print()
    print(f"6. This will download a feedback.json file to: {downloads_folder}")
    print("7. Run the main script again to process the feedback")
    print()
    
    if os.path.exists(feedback_file):
        print(f"✅ Found existing feedback file: {feedback_file}")
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
            
            difficult_words = feedback_data.get('difficultWords', [])
            timestamp = feedback_data.get('timestamp', 'Unknown')
            
            print(f"📅 Feedback timestamp: {timestamp}")
            print(f"📝 Difficult words ({len(difficult_words)}): {', '.join(difficult_words) if difficult_words else 'None'}")
            
            return feedback_data
        except Exception as e:
            print(f"❌ Error reading feedback file: {e}")
    else:
        print(f"⏳ Waiting for feedback file at: {feedback_file}")
    
    return None

if __name__ == "__main__":
    extract_feedback_from_browser()
