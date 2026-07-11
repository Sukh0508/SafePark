import os
import glob

# Django template logic to insert for the Society Dashboard sidebar item
sidebar_item = """        {% if "society" in request.user.profile.account_type|lower %}
        <a href="{% if request.user.profile.society and request.user.profile.society.admin_id == request.user.id %}{% url 'society_admin_dashboard' %}{% else %}{% url 'create_society' %}{% endif %}" style="text-decoration: none;"><button class="nav-item"><span class="nav-icon">🏘</span> Society Dashboard</button></a>
        {% endif %}"""

# We look for the "Scan History" link to inject our new link right after it
marker = "Scan History</button></a>"
marker2 = "Scan History</button></a>"

templates_dir = "/Users/macbook/Desktop/safepark/templates"
files = glob.glob(os.path.join(templates_dir, "*.html"))

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if the file has the sidebar nav and the marker
    if 'class="sidebar-nav"' in content and marker in content:
        # Check if we already inserted it
        if "Society Dashboard" not in content or "create_society" not in content:
            # Replace marker with marker + our new item
            new_content = content.replace(marker, marker + "\n" + sidebar_item)
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Updated {os.path.basename(filepath)}")
        else:
            print(f"Already updated {os.path.basename(filepath)}")

