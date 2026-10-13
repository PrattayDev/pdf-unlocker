import io
import os
from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

# Find template directory dynamically
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
candidate_template_dirs = [
    os.path.join(CURRENT_DIR, 'templates'),
    os.path.join(CURRENT_DIR, 'api', 'templates'),
    os.path.join(os.path.dirname(CURRENT_DIR), 'templates'),
]

template_dir = 'templates'
for c in candidate_template_dirs:
    if os.path.isdir(c) and os.path.exists(os.path.join(c, 'index.html')):
        template_dir = c
        break

app = Flask(__name__, template_folder=template_dir)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max limit

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def check_pdf():
    """PDF ফাইলটিতে পাসওয়ার্ড আছে কিনা তা যাচাই করে।"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'কোনো ফাইল নির্বাচন করা হয়নি'}), 400

    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'শুধুমাত্র PDF ফাইল আপলোড করা যাবে'}), 400

    try:
        pdf_bytes = file.read()
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)

        is_encrypted = reader.is_encrypted
        num_pages = len(reader.pages) if not is_encrypted else None

        return jsonify({
            'success': True,
            'filename': file.filename,
            'size': len(pdf_bytes),
            'is_encrypted': is_encrypted,
            'pages': num_pages
        })
    except PdfReadError:
        return jsonify({'success': False, 'error': 'ফাইলটি ক্ষতিগ্রস্থ (Corrupted) অথবা সঠিক PDF নয়'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'ত্রুটি: {str(e)}'}), 500

@app.route('/api/unlock', methods=['POST'])
def unlock_pdf():
    """পাসওয়ার্ড দিয়ে PDF স্থায়ীভাবে আনলক করে ডাউনলোড ফাইল রিটার্ন করে।"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'কোনো ফাইল নির্বাচন করা হয়নি'}), 400

    file = request.files['file']
    password = request.form.get('password', '')

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'শুধুমাত্র PDF ফাইল গ্রহণ করা হবে'}), 400

    try:
        pdf_bytes = file.read()
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)

        # ১. ফাইলটি এনক্রিপ্ট করা কিনা চেক করা
        if reader.is_encrypted:
            if not password:
                return jsonify({'success': False, 'error': 'এই PDF-টি লক করা। অনুগ্রহ করে পাসওয়ার্ড প্রদান করুন'}), 400

            # ২. পাসওয়ার্ড দিয়ে ডিক্রিপ্ট করা
            decrypt_result = reader.decrypt(password)
            if decrypt_result == 0:
                return jsonify({
                    'success': False,
                    'error': 'ভুল পাসওয়ার্ড! অনুগ্রহ করে সঠিক পাসওয়ার্ডটি দিন।'
                }), 400
        else:
            # অলরেডি আনলকড
            pass

        # ৩. আনলকড PDF তৈরি করা (যাতে আর কখনো পাসওয়ার্ড না লাগে)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if reader.metadata:
            try:
                writer.add_metadata({
                    k: v for k, v in reader.metadata.items()
                    if isinstance(k, str) and isinstance(v, str)
                })
            except Exception:
                pass

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        base_name, _ = os.path.splitext(file.filename)
        download_name = f"{base_name}_unlocked.pdf"

        return send_file(
            output_stream,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_name
        )

    except PdfReadError:
        return jsonify({'success': False, 'error': 'PDF ফাইলটি পড়া সম্ভব হয়নি বা ফাইলটি নষ্ট'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'আনলক করতে সমস্যা হয়েছে: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"==================================================")
    print(f" PDF Unlocker Web App চলছে: http://localhost:{port}")
    print(f"==================================================")
    app.run(host='0.0.0.0', port=port, debug=False)
