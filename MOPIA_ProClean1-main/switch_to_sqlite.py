import os
import re

def switch_to_sqlite():
    settings_path = 'mopia/settings.py'
    
    # Read the current settings file
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    # Find the DATABASES configuration
    db_pattern = re.compile(r'DATABASES\s*=\s*\{.*?\}', re.DOTALL)
    
    # Create the new SQLite configuration
    sqlite_config = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}"""
    
    # Replace the old configuration
    if db_pattern.search(settings_content):
        new_settings = db_pattern.sub(sqlite_config, settings_content)
        
        # Backup the original settings
        os.rename(settings_path, f"{settings_path}.bak")
        
        # Write the new settings
        with open(settings_path, 'w') as f:
            f.write(new_settings)
        
        print("✅ Settings updated to use SQLite! Original settings backed up to settings.py.bak")
        return True
    else:
        print("❌ Could not find DATABASES configuration in settings.py")
        return False

def update_view_to_use_base_no_auth():
    views_path = 'core/views.py'
    
    # Read the current views file
    with open(views_path, 'r') as f:
        views_content = f.read()
    
    # Update the home view to use the base_no_auth.html template
    home_pattern = re.compile(r'def home\(request\):\s*return render\(request, [\'"]home\.html[\'"].*?\)', re.DOTALL)
    home_replacement = "def home(request):\n    return render(request, 'home.html', {'base_template': 'base_no_auth.html'})"
    
    if home_pattern.search(views_content):
        new_views = home_pattern.sub(home_replacement, views_content)
        
        # Backup the original views
        os.rename(views_path, f"{views_path}.bak")
        
        # Write the new views
        with open(views_path, 'w') as f:
            f.write(new_views)
        
        print("✅ Views updated to use base_no_auth.html!")
        return True
    else:
        print("❌ Could not find home view in views.py")
        return False

def update_home_template():
    home_path = 'templates/home.html'
    
    # Read the current home template
    with open(home_path, 'r') as f:
        home_content = f.read()
    
    # Update the template to use the base_template variable
    extends_pattern = re.compile(r'{% extends [\'"]base\.html[\'"] %}')
    extends_replacement = "{% extends base_template|default:'base.html' %}"
    
    if extends_pattern.search(home_content):
        new_home = extends_pattern.sub(extends_replacement, home_content)
        
        # Backup the original home template
        os.rename(home_path, f"{home_path}.bak")
        
        # Write the new home template
        with open(home_path, 'w') as f:
            f.write(new_home)
        
        print("✅ Home template updated to use the base_template variable!")
        return True
    else:
        print("❌ Could not find extends tag in home.html")
        return False

if __name__ == "__main__":
    print("Switching to SQLite database and making template adjustments...")
    
    switch_success = switch_to_sqlite()
    view_success = update_view_to_use_base_no_auth()
    template_success = update_home_template()
    
    if switch_success and view_success and template_success:
        print("\n✅ All changes applied successfully!")
        print("\nNext steps:")
        print("1. Run: python manage.py migrate")
        print("2. Restart your Django server")
        print("3. Try accessing http://127.0.0.1:8000/ again")
    else:
        print("\n⚠️ Some changes could not be applied. Check the errors above.")
```
