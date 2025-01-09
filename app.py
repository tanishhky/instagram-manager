import logging
import time
from flask import Flask, render_template, request, redirect, session, jsonify
from instagrapi import Client
from instagrapi.exceptions import ClientLoginRequired, PleaseWaitFewMinutes
import json # Import the json module

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key!

# Global variable to store the Instagrapi client
cl = None

@app.route('/')
def index():
    global cl
    if cl:
        return redirect('/non_followers')
    return render_template('login.html')  # Display login page

@app.route('/login', methods=['POST'])
def login():
    global cl
    data = request.json
    username = data.get("username")
    password = data.get("password")
    logging.info(f"Login attempt with username: {username}")

    try:
        # Initialize client here for better security
        cl = Client()
        cl.login(username, password)
        logging.info(f"Login successful for username: {username}")
        return jsonify({"message": "Login successful"}), 200
    except (ClientLoginRequired, PleaseWaitFewMinutes) as e:
        logging.error(f"Login failed: Rate limit error: {str(e)}")
        return jsonify({"error": "Rate limit exceeded. Please wait a few minutes."}), 429
    except Exception as e:
        logging.error(f"Login failed for username: {username}, Error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/non_followers', methods=['GET'])
def non_followers():
    global cl
    if not cl:
        logging.warning("Access to /non_followers without login.")
        return jsonify({"error": "Not logged in"}), 401

    logging.info("Fetching non-followers list...")
    try:
        user_id = cl.user_id
        logging.info(f"Fetched user_id: {user_id}")

        followers = set(cl.user_followers(user_id, amount=0))  # Use amount=0 for all
        logging.info(f"Followers fetched. Count: {len(followers)}")

        following = set(cl.user_following(user_id, amount=0))  # Use amount=0 for all
        logging.info(f"Following fetched. Count: {len(following)}")

        non_followers = list(following - followers)
        logging.info(f"Non-followers count (raw calculation): {len(non_followers)}")

        # Debugging: Log followers and following counts before calculating the difference.
        logging.info(f"Followers count: {len(followers)}")
        logging.info(f"Following count: {len(following)}")

        # Fetch detailed user info for non-followers
        non_followers_details = []
        for i, uid in enumerate(non_followers):
            # Introduce a delay to avoid rate limiting
            if i > 0 and i % 10 == 0:  # Delay every 10 users
                logging.info(f"Pausing for rate limiting (processed {i} users)...")
                time.sleep(2)  # Adjust the delay as needed

            try:
                user_info = cl.user_info(uid)
                non_followers_details.append({
                    "username": user_info.username,
                    "id": uid,
                    "profile_pic": user_info.profile_pic_url
                })
            except json.JSONDecodeError as e:
                logging.error(f"Error fetching user info for user ID {uid}: JSONDecodeError: {str(e)}")
                non_followers_details.append({
                    "username": f"Error fetching info (user ID: {uid})",
                    "id": uid,
                    "profile_pic": "" # You can use a default image URL here
                })
            except Exception as e:
                logging.error(f"Error fetching user info for user ID {uid}: {str(e)}")
                non_followers_details.append({
                    "username": f"Error fetching info (user ID: {uid})",
                    "id": uid,
                    "profile_pic": ""
                })

        logging.info(f"Non-followers details fetched. Count: {len(non_followers_details)}")
        return jsonify(non_followers_details), 200
    except (ClientLoginRequired, PleaseWaitFewMinutes) as e:
        logging.error(f"Fetching non-followers failed: Rate limit error: {str(e)}")
        return jsonify({"error": "Rate limit exceeded. Please wait a few minutes."}), 429
    except Exception as e:
        logging.error(f"Error fetching non-followers: {str(e)}")
        return jsonify({"error": str(e)}), 400
    

    
@app.route('/unfollow/<user_id>', methods=['POST'])
def unfollow(user_id):
    global cl
    if not cl:
        logging.warning("Attempt to unfollow without login.")
        return jsonify({"error": "Not logged in"}), 401
    logging.info(f"Attempting to unfollow user ID: {user_id}")
    try:
        cl.user_unfollow(user_id)
        logging.info(f"Successfully unfollowed user ID: {user_id}")
        return jsonify({"message": f"Unfollowed user {user_id} successfully"}), 200
    except Exception as e:
        logging.error(f"Error unfollowing user ID: {user_id}, Error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/logout', methods=['GET'])
def logout():
    global cl
    if cl:
        try:
            cl.logout()
        except Exception as e:
            logging.error(f"Error during logout: {str(e)}")
            # Decide how to handle logout errors - force clear session anyway or show error
        cl = None
    session.clear()
    logging.info("User logged out successfully")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)