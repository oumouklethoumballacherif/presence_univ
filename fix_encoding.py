
import os

file_path = 'app/routes/admin.py'

try:
    with open(file_path, 'rb') as f:
        content = f.read()

    # The file likely has normal UTF-8 content, followed by the PowerShell appended content (UTF-16 LE)
    # PowerShell >> might produce \r\n then BOM \xff\xfe then content
    
    # Let's try to identify where it went wrong. 
    # We essentially want to strip all null bytes if they are interstitial, or handle the appended part.
    # Simple fix for "source code string cannot contain null bytes": remove them.
    # But if it's UTF-16, removing nulls `\x00` from `a\x00` leaves `a`. This works for ASCII range characters in UTF-16.
    
    clean_content = content.replace(b'\x00', b'')
    
    # Also remove the BOM if it exists in the middle
    clean_content = clean_content.replace(b'\xff\xfe', b'')
    
    with open(file_path, 'wb') as f:
        f.write(clean_content)
        
    print(f"Successfully cleaned {file_path}")

except Exception as e:
    print(f"Error: {e}")
