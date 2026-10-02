from app import app
from controllers.laporan import index
from flask import session

with app.app_context():
    with app.test_request_context('/laporan'):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'admin'
                sess['role'] = 'admin'
            response = client.get('/laporan/')
            print("Status Code:", response.status_code)
            if response.status_code != 200:
                print("Response data:")
                print(response.data.decode('utf-8'))
