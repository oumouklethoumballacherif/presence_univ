from app import create_app
from app.models import User
import datetime

app = create_app()

with app.app_context():
    # 1. Get the latest student to retrieve the REAL token
    student = User.query.filter_by(role='student').order_by(User.created_at.desc()).first()
    if not student:
        print("No student found")
        exit()
        
    real_token = student.token
    print(f"Real Token in DB: '{real_token}'")
    print(f"Token Length: {len(real_token)}")
    
    # 2. Try to find user by this token
    found_user = User.query.filter_by(token=real_token).first()
    if found_user:
        print(f"✓ Success: Found user {found_user.email} by exact token.")
    else:
        print(f"❌ Failed: Could not find user by exact token.")
        
    # 3. Simulate the route logic exactly
    print("\nSimulating route logic checking...")
    user = User.query.filter_by(token=real_token).first()
    
    if not user:
        print("-> User not found by token")
    elif not user.verify_token():
        print("-> User found but verify_token() returned False")
        print(f"   Expiry: {user.token_expiry}")
        print(f"   Now:    {datetime.datetime.utcnow()}")
    else:
        print("-> ✓ Route logic should succeed (User found and token valid)")
        
    # 4. Check for URL safety or weird chars
    import urllib.parse
    quoted = urllib.parse.quote(real_token)
    print(f"\nURL Encoded token: {quoted}")
    if real_token != quoted:
        print("! Warning: Token contains characters that change correctly when URL encoded.")
        print("  Can lead to mismatch if Flask/Browser decodes differently.")
    else:
        print("Token is URL-safe (no changes when encoded).")
