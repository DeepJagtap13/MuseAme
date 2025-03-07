import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import pytz  # Import pytz for timezone support

app = Flask(__name__)

app.secret_key = os.urandom(24)
app.config['SESSION_PERMANENT'] = False

genai.configure(api_key="AIzaSyDN93NyjlOTcMOcA3pw6insw2AQGqkDy7k")  # **REPLACE WITH YOUR ACTUAL API KEY**

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

museums_mumbai = {
    "Chhatrapati Shivaji Maharaj Vastu Sangrahalaya": "https://www.google.com/maps/place/Chhatrapati+Shivaji+Maharaj+Vastu+Sangrahalaya/@18.9269015,72.8326916,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1c3eaf8b127:0x44e72610553e9253!8m2!3d18.9269015!4d72.8326916!16zL20vMDIweHFq?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "Bhau Daji Lad Museum": "https://www.google.com/maps/place/Dr.+Bhau+Daji+Lad+Museum/@18.978994,72.832235,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7ce5b428e70af:0x79efde6c140c2e05!8m2!3d18.9789889!4d72.8348153!16s%2Fm%2F06w4mwg?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "RBI Monetary Museum": "https://www.google.com/maps/place/RBI+Monetary+Museum/@18.9338384,72.8335049,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1db04fcb821:0x23fdb1a2c72d48fd!8m2!3d18.9338333!4d72.8360852!16s%2Fg%2F1hhk3qlt5?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "BEST Transport Museum": "https://www.google.com/maps/search/BEST+Transport+Museum/@19.0466621,72.8752297,17z/data=!3m1!4b1?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "Mani Bhavan Gandhi Museum": "https://www.google.com/maps/place/Mani+Bhavan+Gandhi+Sangrahalaya/@18.9598504,72.8089349,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7ce0c69115555:0xc0b175f791f839fd!8m2!3d18.9598453!4d72.8115152!16zL20vMGI4M3Qx?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "National Gallery of Modern Art, Mumbai": "https://www.google.com/maps/place/National+Gallery+of+Modern+Art/@18.9257775,72.8288663,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1c3d69e9505:0x33783085c701ece!8m2!3d18.9257724!4d72.8314466!16s%2Fm%2F0r4lnv5?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "Bombay Natural History Society (BNHS) Museum": "https://www.google.com/maps/place/Bombay+Natural+History+Society/@18.9262191,72.8306906,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7d1dcc331fcdf:0x882326d15726feb1!8m2!3d18.926214!4d72.8332709!16s%2Fg%2F1tf274bd?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",
    "Dr. Bhau Daji Lad Museum": "https://www.google.com/maps/place/Dr.+Bhau+Daji+Lad+Museum/@18.978994,72.832235,17z/data=!3m1!4b1!4m6!3m5!1s0x3be7ce5b428e70af:0x79efde6c140c2e05!8m2!3d18.9789889!4d72.8348153!16s%2Fm%2F06w4mwg?entry=ttu&g_ep=EgoyMDI1MDIwMy4wIKXMDSoASAFQAw%3D%3D",  # Correct if different
    "Maharashtra State Police Museum": None,
    "Nehru Science Centre": None,
}

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

@app.route('/')
def index():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input'].lower()
    response = ""

    # Sync today's date with Asia/Kolkata timezone (Mumbai's timezone)
    if "today's date" in user_input or "what is the date" in user_input:
        tz = pytz.timezone('Asia/Kolkata')
        response = f"Today's date is {datetime.now(tz).strftime('%B %d, %Y')}."
    elif "list of museums in mumbai" in user_input:
        response = "Here are some prominent museums in Mumbai:\n"
        for i, museum_name in enumerate(museums_mumbai, 1):
            response += f"{i}. {museum_name}\n"
    elif "gmaps link for" in user_input or "google maps link for" in user_input or "location of" in user_input or "where is" in user_input:
        found_museum = False
        for museum_name in museums_mumbai:
            if museum_name.lower() in user_input:
                link = museums_mumbai.get(museum_name)
                if link:
                    response += f"Here is the Google Maps link for {museum_name}: <a href='{link}' target='_blank'>{link}</a>\n"
                    found_museum = True
                else:
                    response += f"Sorry, Google Maps link not available for {museum_name}\n"
                    found_museum = True
                break
        if not found_museum:
            response = GenerateResponse(user_input, "\n".join([f"User: {msg['user']}\nBot: {msg['bot']}" for msg in session['chat_history']]))
    else:
        response = GenerateResponse(user_input, "\n".join([f"User: {msg['user']}\nBot: {msg['bot']}" for msg in session['chat_history']]))
    
    session['chat_history'].append({'user': user_input, 'bot': response})
    session.modified = True
    return jsonify({'response': response})



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Default to 10000
    app.run(host='0.0.0.0', port=port)
