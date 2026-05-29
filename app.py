from flask import Flask, request, jsonify
from pypdf import PdfReader, PdfWriter
import requests
import os
import io

app = Flask(__name__)

def fill_lp3(data):
    reader = PdfReader("LP3-Form-to-notify-people.pdf")
    writer = PdfWriter()
    writer.append(reader)

    fields = {
        "Title": data.get("notify_title", ""),
        "First names": data.get("notify_first_name", ""),
        "Last name": data.get("notify_last_name", ""),
        "Address 1": data.get("notify_address1", ""),
        "Address 2": data.get("notify_address2", ""),
        "Address 3": data.get("notify_address3", ""),
        "undefined": data.get("notify_postcode", ""),
        "Day": data.get("notify_day", ""),
        "Month": data.get("notify_month", ""),
        "Year": data.get("notify_year", ""),
        "Title_2": data.get("donor_title", ""),
        "First names_2": data.get("donor_first_name", ""),
        "Last name_2": data.get("donor_last_name", ""),
        "Address 1_2": data.get("donor_address1", ""),
        "Address 2_2": data.get("donor_address2", ""),
        "Address 3_2": data.get("donor_address3", ""),
        "undefined_2": data.get("donor_postcode", ""),
        "When did the donor sign the LPA": data.get("donor_signed_day", ""),
        "Month_2": data.get("donor_signed_month", ""),
        "Year_2": data.get("donor_signed_year", ""),
        "Title_3": data.get("attorney1_title", ""),
        "First names_3": data.get("attorney1_first_name", ""),
        "Last name_3": data.get("attorney1_last_name", ""),
        "Address 1_3": data.get("attorney1_address1", ""),
        "Address 2_3": data.get("attorney1_address2", ""),
        "Address 3_3": data.get("attorney1_address3", ""),
        "undefined_3": data.get("attorney1_postcode", ""),
        "Title_4": data.get("attorney2_title", ""),
        "First names_4": data.get("attorney2_first_name", ""),
        "Last name_4": data.get("attorney2_last_name", ""),
        "Address 1_4": data.get("attorney2_address1", ""),
        "Address 2_4": data.get("attorney2_address2", ""),
        "Address 3_4": data.get("attorney2_address3", ""),
        "undefined_4": data.get("attorney2_postcode", ""),
        "register lpa": data.get("register_lpa", "Donor"),
        "type lpa": data.get("type_lpa", "Property and financial affairs"),
        "attorney appointed": data.get("attorney_appointed", ""),
    }

    for page in writer.pages:
        writer.update_page_form_field_values(page, fields, auto_regenerate=False)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def fill_lpc(data):
    reader = PdfReader("LPC-Continuation-sheets.pdf")
    writer = PdfWriter()
    writer.append(reader)

    fields = {
        "Title": data.get("person1_title", ""),
        "First names": data.get("person1_first_name", ""),
        "Last name": data.get("person1_last_name", ""),
        "Date of birth not required for person to notify": data.get("person1_dob", ""),
        "Month": data.get("person1_dob_month", ""),
        "Year": data.get("person1_dob_year", ""),
        "Address 1": data.get("person1_address1", ""),
        "Address 2": data.get("person1_address2", ""),
        "Address 3": data.get("person1_address3", ""),
        "undefined": data.get("person1_postcode", ""),
        "Email address optional": data.get("person1_email", ""),
        "Title_2": data.get("person2_title", ""),
        "First names_2": data.get("person2_first_name", ""),
        "Last name_2": data.get("person2_last_name", ""),
        "Date of birth not required for person to notify_2": data.get("person2_dob", ""),
        "Month_2": data.get("person2_dob_month", ""),
        "Year_2": data.get("person2_dob_year", ""),
        "Address 1_2": data.get("person2_address1", ""),
        "Address 2_2": data.get("person2_address2", ""),
        "Address 3_2": data.get("person2_address3", ""),
        "undefined_2": data.get("person2_postcode", ""),
        "Email address optional_2": data.get("person2_email", ""),
        "Full name": data.get("donor_full_name", ""),
        "Date signed or marked": data.get("donor_signed_date", ""),
        "Instructions LPA section 7": data.get("additional_info", ""),
        "Full name_3": data.get("donor_full_name", ""),
        "Date signed or marked_3": data.get("donor_signed_date", ""),
    }

    for page in writer.pages:
        writer.update_page_form_field_values(page, fields, auto_regenerate=False)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def save_to_ghl(contact_id, pdf_bytes, filename, api_key):
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}/notes"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }
    import base64
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    payload = {"body": f"Completed PDF: {filename}", "attachments": [pdf_base64]}
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code


@app.route("/fill-lpa", methods=["POST"])
def fill_lpa_webhook():
    try:
        data = request.json
        api_key = os.environ.get("GHL_API_KEY", "")
        contact_id = data.get("contact_id", "")

        lp3_pdf = fill_lp3(data)
        lpc_pdf = fill_lpc(data)

        if contact_id and api_key:
            save_to_ghl(contact_id, lp3_pdf, "LP3-completed.pdf", api_key)
            save_to_ghl(contact_id, lpc_pdf, "LPC-completed.pdf", api_key)

        return jsonify({"status": "success", "message": "PDFs filled and saved to GHL"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return "LPA PDF Auto Fill is running!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
