
import unittest
from app import create_app, db
from app.models import User, Department, Track, AcademicYear
from app.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = True # Important: Enable CSRF for testing our fix
    SECRET_KEY = 'test-secret-key'

class FullAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        # db.create_all() is already called in create_app

        # Get existing Admin created by create_app
        self.admin = User.query.filter_by(email='admin@uir.ac.ma').first()
        # Ensure password is known for login
        self.admin.set_password('admin123')
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, email, password):
        # 1. Get Login Page to get CSRF Token
        response = self.client.get('/login')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        token_input = soup.find('input', {'name': 'csrf_token'})
        csrf_token = token_input['value'] if token_input else ''
        
        # 2. Post Login
        return self.client.post('/login', data=dict(
            email=email,
            password=password,
            csrf_token=csrf_token
        ), follow_redirects=True)

    def test_admin_login(self):
        """Test that admin can login"""
        response = self.login('admin@uir.ac.ma', 'admin123')
        self.assertIn(b'Super Admin', response.data)
        self.assertEqual(response.status_code, 200)

    def test_csrf_protection_on_delete_student(self):
        """Test student deletion with and without CSRF token"""
        # 1. Login
        self.login('admin@uir.ac.ma', 'admin123')

        # 2. Create a dummy student to delete
        student = User(email='student@test.com', first_name='John', last_name='Doe', role='student', matricule='S12345')
        db.session.add(student)
        db.session.commit()
        student_id = student.id

        # 3. Attempt Delete WITHOUT CSRF token (Should Fail with 400 or Redirect depending on config, usually 400 Bad Request)
        # Note: Flask-WTF CSRF behavior depends on configuration. 
        # By default, it returns 400.
        
        # Manually constructing headers/data to simulate missing token
        response = self.client.post(f'/admin/students/{student_id}/delete')
        self.assertEqual(response.status_code, 400, "Should return 400 Bad Request if CSRF token is missing")
        self.assertIn(b'The CSRF token is missing', response.data)

        # 4. Attempt Delete WITH CSRF token (Should Succeed)
        # We need to get a token first. 
        # In test client, we can inspect cookies or headers, OR we can parse it from a form.
        # But simpler way in Flask-Testing is often just to ensure the token is generated.
        
        # However, since we want to verify the 'fetch' logic works, strictly speaking we are testing the SERVER side handling here.
        # The fixes I made were CLIENT side (JavaScript).
        # But checking that the server ACCEPTs the token is key.

        # Let's verify the server-side deletion route works when provided with a valid token.
        
        with self.client:
            # Get a fresh token by visiting a page
            response = self.client.get('/admin/students')
            # The client cookie jar now has the csrf_token if it's cookie based, 
            # but Flask-WTF usually puts it in the DOM. 
            # Actually, `test_client` handles cookies automatically. 
            # But for `CSRFProtect`, we probably need to send `X-CSRFToken` header or form data.
            
            # Extract CSRF token from the DOM of the response
            csrf_token = None
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.data, 'html.parser')
            # Look for the hidden input we added
            token_input = soup.find('input', {'name': 'csrf_token'})
            if token_input:
                csrf_token = token_input['value']
            
            self.assertIsNotNone(csrf_token, "Could not find CSRF token in the page")

            # Perform the delete with the token
            response = self.client.post(f'/admin/students/{student_id}/delete', data={'csrf_token': csrf_token}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'supprim\xc3\xa9 avec succ\xc3\xa8s', response.data) # "supprimé avec succès" in bytes

            # Verify deletion
            deleted_student = User.query.get(student_id)
            self.assertIsNone(deleted_student)

    def test_create_and_delete_flow(self):
        """Test full flow: Create, List, Delete"""
        self.login('admin@uir.ac.ma', 'admin123')

        # 1. Create a Department & Track (Required for creating student via form usually, though model allows nullable)
        # Let's stick to the minimal model creation for the test to be robust.
        
        # 2. Setup Data
        student = User(email='delete_me@test.com', first_name='Delete', last_name='Me', role='student', matricule='DEL001')
        db.session.add(student)
        db.session.commit()
        
        # 3. Get CSRF Token
        response = self.client.get('/admin/students')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        token_input = soup.find('input', {'name': 'csrf_token'})
        csrf_token = token_input['value']

        # 4. Delete
        response = self.client.post(f'/admin/students/{student.id}/delete', data={'csrf_token': csrf_token}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(User.query.get(student.id))

if __name__ == '__main__':
    unittest.main()
