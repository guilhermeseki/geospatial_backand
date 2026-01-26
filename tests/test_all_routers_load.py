"""
Test that all routers load correctly with the sys.path fix.
Verifies that the modification to main.py doesn't break existing routers.
"""

# Fix imports to work from any directory
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 80)
print("Testing All Router Imports")
print("=" * 80)
print(f"Project root: {project_root}")
print(f"Python path includes project root: {str(project_root) in sys.path}")
print()

routers_to_test = [
    ('precipitation', 'app.api.routers.precipitation'),
    ('temperature', 'app.api.routers.temperature'),
    ('ndvi', 'app.api.routers.ndvi'),
    ('wind', 'app.api.routers.wind'),
    ('lightning', 'app.api.routers.lightning'),
    ('solar', 'app.api.routers.solar'),
    ('georisk', 'app.api.routers.georisk'),
    ('locations', 'app.api.routers.locations'),
]

success_count = 0
failed_count = 0

for name, module_path in routers_to_test:
    try:
        # Try to import the router
        module = __import__(module_path, fromlist=['router'])
        router = getattr(module, 'router', None)

        if router is None:
            print(f"❌ {name:15} - No 'router' attribute found")
            failed_count += 1
        else:
            # Check if it's a valid APIRouter
            from fastapi import APIRouter
            if isinstance(router, APIRouter):
                print(f"✅ {name:15} - Loaded successfully")
                success_count += 1
            else:
                print(f"⚠️  {name:15} - 'router' is not an APIRouter instance")
                failed_count += 1

    except ImportError as e:
        print(f"❌ {name:15} - Import failed: {e}")
        failed_count += 1
    except Exception as e:
        print(f"❌ {name:15} - Error: {e}")
        failed_count += 1

print()
print("=" * 80)
print(f"Results: {success_count} passed, {failed_count} failed")
print("=" * 80)

if failed_count > 0:
    print("⚠️  Some routers failed to load!")
    sys.exit(1)
else:
    print("✅ All routers loaded successfully!")
    sys.exit(0)
