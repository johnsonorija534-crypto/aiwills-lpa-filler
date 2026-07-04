from flask import Flask, request, jsonify, send_from_directory
from pypdf import PdfReader, PdfWriter
import os, io, requests, threading
from datetime import datetime

app = Flask(__name__)
GHL_API_KEY = 'pit-41146bbe-c1a9-4e7e-904f-de91d98d7ffd'
LOCATION_ID = 'MzVD4CHOWxTi5fTfeZSh'
SAVE_DIR = '/var/www/lpa-filler/completed_pdfs'
os.makedirs(SAVE_DIR, exist_ok=True)

def fill_pdf(template_path, fields):
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, fields)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def send_to_ghl(contact_id, location_id, lp3_link, lpc_link, donor_name):
    try:
        headers = {
            'Authorization': f'Bearer {GHL_API_KEY}',
            'Version': '2021-07-28',
            'Content-Type': 'application/json'
        }
        conv = requests.post(
            'https://services.leadconnectorhq.com/conversations/',
            headers=headers,
            json={'contactId': contact_id, 'locationId': location_id},
            timeout=15
        )
        print(f"Conv: {conv.status_code} {conv.text[:200]}")
        conv_data = conv.json()
        conv_id = conv_data.get('conversation', {}).get('id') or conv_data.get('id')
        print(f"Conv ID: {conv_id}")
        if conv_id:
            body = f"LPA PDFs ready for {donor_name}\n\nLP3 Form: {lp3_link}\n\nLPC Form: {lpc_link}"
            msg = requests.post(
                'https://services.leadconnectorhq.com/conversations/messages',
                headers=headers,
                json={
                    'type': 'TYPE_INTERNAL_COMMENT',
                    'conversationId': str(conv_id),
                    'body': body,
                    'html': f'<p>LPA PDFs for {donor_name}</p><p><a href="{lp3_link}">LP3 Download</a></p><p><a href="{lpc_link}">LPC Download</a></p>'
                },
                timeout=15
            )
            print(f"Msg: {msg.status_code} {msg.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

@app.route('/')
def index():
    return 'LPA PDF Auto Fill is running!'

@app.route('/download/<filename>')
def download_pdf(filename):
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)

@app.route('/fill-lpa', methods=['POST'])
def fill_lpa():
    data = request.json or {}
    contact_id = data.get('contact_id', '')
    location_id = data.get('location_id', '') or LOCATION_ID
    donor_first = data.get('donor_first_name', '') or data.get('donor_first_n', 'Unknown')
    donor_last = data.get('donor_last_name', '') or data.get('donor_last_n', 'User')
    donor_name = f"{donor_first} {donor_last}"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"Request: {donor_name} | contact: {contact_id} | location: {location_id}")
    lp3_fields = {
        'First names_2': donor_first,
        'Last name_2': donor_last,
        'Address 1_2': data.get('donor_address1', '') or data.get('donor_addres', ''),
        'First names_3': data.get('attorney1_first_name', '') or data.get('attorney1_firs', ''),
        'Last name_3': data.get('attorney1_last_name', '') or data.get('attorney1_last', ''),
        'First names': data.get('notify_first_name', '') or data.get('notify_first_na', ''),
        'Last name': data.get('notify_last_name', '') or data.get('notify_last_na', ''),
    }
    lpc_fields = {'Full name': donor_name}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lp3_pdf = fill_pdf(os.path.join(base_dir, 'LP3-Form-to-notify-people.pdf'), lp3_fields)
    lpc_pdf = fill_pdf(os.path.join(base_dir, 'LPC-Continuation-sheets.pdf'), lpc_fields)
    lp3_file = f'LP3_{donor_first}_{donor_last}_{timestamp}.pdf'
    lpc_file = f'LPC_{donor_first}_{donor_last}_{timestamp}.pdf'
    with open(os.path.join(SAVE_DIR, lp3_file), 'wb') as f:
        f.write(lp3_pdf.getvalue())
    with open(os.path.join(SAVE_DIR, lpc_file), 'wb') as f:
        f.write(lpc_pdf.getvalue())
    lp3_link = f'http://162.0.213.130:5000/download/{lp3_file}'
    lpc_link = f'http://162.0.213.130:5000/download/{lpc_file}'
    print(f"LP3: {lp3_link}")
    print(f"LPC: {lpc_link}")
    threading.Thread(target=send_to_ghl, args=(contact_id, location_id, lp3_link, lpc_link, donor_name), daemon=True).start()
    return jsonify({'status': 'success', 'lp3': lp3_link, 'lpc': lpc_link})

if __name__ == '__main__':
    app.run(debug=True)
