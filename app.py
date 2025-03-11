import os
import base64
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from datetime import datetime
import pytz
import mysql.connector
import requests
import json
import traceback
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

app.secret_key = os.urandom(24)
app.config['SESSION_PERMANENT'] = False

# Replace with your actual Google API key
genai.configure(api_key="AIzaSyDN93NyjlOTcMOcA3pw6insw2AQGqkDy7k")

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

# Museum names in lowercase for case-insensitive matching
museums_mumbai = {
    "chhatrapati shivaji maharaj vastu sangrahalaya": "https://www.google.com/maps/place/Chhatrapati+Shivaji+Maharaj+Vastu+Sangrahalaya/@18.9269015,72.8326916,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1c3eaf8b127:0x44e72610553e9253!8m2!3d18.9269015!4d72.8326916!16zL20vMDIweHFq?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "bhau daji lad museum": "https://www.google.com/maps/place/Dr.+Bhau+Daji+Lad+Museum/@18.978994,72.832235,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7ce5b428e70af:0x79efde6c140c2e05!8m2!3d18.9789889!4d72.8348153!16s%2Fm%2F06w4mwg?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "rbi monetary museum": "https://www.google.com/maps/place/RBI+Monetary+Museum/@18.9338384,72.8335049,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1db04fcb821:0x23fdb1a2c72d48fd!8m2!3d18.9338333!4d72.8360852!16s%2Fg%2F1hhk3qlt5?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "best transport museum": "https://www.google.com/maps/search/BEST+Transport+Museum/@19.0466621,72.8752297,17z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "mani bhavan gandhi museum": "https://www.google.com/maps/place/Mani+Bhavan+Gandhi+Sangrahalaya/@18.9598504,72.8089349,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7ce0c69115555:0xc0b175f791f839fd!8m2!3d18.9598453!4d72.8115152!16zL20vMGI4M3Qx?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "national gallery of modern art, mumbai": "https://www.google.com/maps/place/National+Gallery+of+Modern+Art/@18.9257775,72.8288663,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1c3d69e9505:0x33783085c701ece!8m2!3d18.9257724!4d72.8314466!16s%2Fm%2F0r4lnv5?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "bombay natural history society (bnhs) museum": "https://www.google.com/maps/place/Bombay+Natural+History+Society/@18.9262191,72.8306906,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1dcc331fcdf:0x882326d15726feb1!8m2!3d18.926214!4d72.8332709!16s%2Fg%2F1tf274bd?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "maharashtra state police museum": None,
    "nehru science centre": None,
}

RAZORPAY_KEY_ID = "rzp_test_grMytIcY5TuC0o"  # Your Razorpay Key ID
RAZORPAY_SECRET = "tOiaCUJf4hf36OD9QgK3ftL1"  # Your Razorpay Secret

# Email configuration (for testing with Gmail)
EMAIL_ADDRESS = "museame05@gmail.com"  # Replace with your Gmail address
EMAIL_PASSWORD = "qufx pttz btsl tvbz"    # Replace with your Gmail App Password (use App Password for 2FA)

def GenerateResponse(input_text, chat_history):
    prompt = (
        "You are a chatbot that deals majorly in museums. "
        "Provide information about museums. For booking tickets, handle it only for museums in Mumbai. "
        "Give a list of museums when requested, and for each, provide basic information, location, and history if asked. "
        "Keep answers short and simple unless the user asks for detailed history. "
        "When the user asks for the list of museums, give the list of at least 10 prominent museums in that city. "
        "When the user asks for locations to dine in near the museum, suggest restaurants or cafes near the museums. "
        "Booking of the tickets should be done only for the museums available in Mumbai, not any other museum outside Mumbai. "
        "You should also answer the basic general knowledge question. "
        "Use the following chat history to maintain context: \n"
        f"{chat_history}\n"
        f"input: {input_text}\n"
        "output: "
    )

    response = model.generate_content([prompt])
    return response.text

def store_booking_data(booking_data):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # Replace with your MySQL username
            password='',  # Replace with your MySQL password
            database='deep'  # Replace with your MySQL database name
        )
        cursor = connection.cursor()
        sql = "INSERT INTO bookings (museum_name, date, num_visitors, visitor_names, email) VALUES (%s, %s, %s, %s, %s)"
        values = (booking_data['museum_name'], booking_data['date'], booking_data['num_visitors'], booking_data['visitor_names'], booking_data['email'])
        cursor.execute(sql, values)
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except mysql.connector.Error as err:
        print(f"Failed to store booking data: {err}")
        return False

def openRazorpay(amount):
    auth_string = f"{RAZORPAY_KEY_ID}:{RAZORPAY_SECRET}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_auth}'
    }
    
    order_data = {
        "amount": amount * 100,  # Amount in paise
        "currency": "INR",
        "receipt": "receipt#1",
        "payment_capture": 1  # Auto capture
    }
    
    try:
        response = requests.post("https://api.razorpay.com/v1/orders", headers=headers, data=json.dumps(order_data))
        if response.status_code == 200:
            order_response = response.json()
            return order_response['id']
        else:
            print(f"Error creating Razorpay order: Status Code {response.status_code}, Response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Failed to connect to Razorpay: {e}")
        return None

def send_booking_email(booking_data, order_id):
    msg = MIMEText(f"""
    Subject: Museum Ticket Booking Confirmation

    Dear {booking_data['visitor_names'].split(',')[0].strip()},

    Thank you for booking tickets with us! Below are your booking details:

    - Museum: {booking_data['museum_name'].title()}
    - Date: {booking_data['date']}
    - Number of Visitors: {booking_data['num_visitors']}
    - Visitor Names: {booking_data['visitor_names']}
    - Order ID: {order_id}
    - Total Amount: ₹{int(booking_data['num_visitors']) * 500}

    Please keep this email for your records. Enjoy your visit!

    Best regards,
    MuseAme
    """)
    msg['Subject'] = 'Museum Ticket Booking Confirmation'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = booking_data['email']

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent successfully to {booking_data['email']}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/')
def index():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('index.html')

@app.route('/admin.html')
def admin():
    return render_template('admin.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/ask', methods=['POST'])
def ask():
    try:
        user_input = request.form['user_input'].lower()
        print(f"User Input: {user_input}")
        print(f"Session Booking Data: {session.get('booking_data', 'No booking data')}")

        response = ""

        if "book" in user_input or "ticket" in user_input or "booking" in user_input:
            session['booking_data'] = {}
            session['booking_data']['step'] = 'museum_name'
            response = "Please provide the museum name."
        elif session.get('booking_data', {}).get('step') == 'museum_name':
            if user_input in museums_mumbai:
                session['booking_data']['museum_name'] = user_input
                session['booking_data']['step'] = 'date'
                response = "Please provide the date of visit (e.g., March 11, 2025)."
            else:
                response = "Sorry, I can only book tickets for museums in Mumbai. Please choose a valid museum from the list."
        elif session.get('booking_data', {}).get('step') == 'date':
            try:
                # Basic date validation
                datetime.strptime(user_input, '%B %d, %Y')
                session['booking_data']['date'] = user_input
                session['booking_data']['step'] = 'visitors'
                response = "How many visitors will be there?"
            except ValueError:
                response = "Invalid date format. Please use 'Month Day, Year' (e.g., March 11, 2025)."
        elif session.get('booking_data', {}).get('step') == 'visitors':
            if user_input.isdigit() and int(user_input) > 0:
                session['booking_data']['num_visitors'] = user_input
                session['booking_data']['step'] = 'names'
                response = "Please provide the names of the visitors (comma-separated)."
            else:
                response = "Please enter a valid number of visitors (e.g., 2)."
        elif session.get('booking_data', {}).get('step') == 'names':
            session['booking_data']['visitor_names'] = user_input
            session['booking_data']['step'] = 'email'
            response = "Please provide your email address for booking confirmation."
        elif session.get('booking_data', {}).get('step') == 'email':
            # Basic email validation (can be enhanced with regex)
            if '@' in user_input and '.' in user_input:
                session['booking_data']['email'] = user_input
                num_visitors = int(session['booking_data']['num_visitors'])
                amount = num_visitors * 500  # Assuming 500 INR per ticket
                order_id = openRazorpay(amount)
                
                if order_id:
                    if store_booking_data(session['booking_data']):
                        send_booking_email(session['booking_data'], order_id)
                        session.pop('booking_data', None)  # Clear booking data after successful booking
                        return jsonify({
                            "message": "Redirecting you to the payment gateway...",
                            "order_id": order_id,
                            "amount": amount,  # Fixed typo from "amount amount"
                            "key_id": RAZORPAY_KEY_ID,
                            "email": user_input  # Use the provided email
                        })
                    else:
                        response = "Failed to store booking data. Please try again."
                        session.pop('booking_data', None)
                else:
                    response = "There was an error creating the payment order. Please try again."
                    session.pop('booking_data', None)
            else:
                response = "Invalid email address. Please provide a valid email (e.g., example@domain.com)."
        else:
            response = GenerateResponse(user_input, "\n".join([f":User    {msg['user']}\nBot: {msg['bot']}" for msg in session['chat_history']]))
        
        session['chat_history'].append({'user': user_input, 'bot': response})
        session.modified = True
        return jsonify({'response': response})

    except Exception as e:
        print(f"Internal Server Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'response': f"An internal error occurred: {str(e)}. Please try again later."}), 500

@app.route('/payment_callback', methods=['POST'])
def payment_callback():
    try:
        data = request.get_json()
        return jsonify({'status': 'success', 'message': 'Your tickets have been booked successfully.'})
    except Exception as e:
        print(f"Payment Callback Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'response': 'Error processing payment callback.'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)