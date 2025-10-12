import os
import random
import subprocess
from datetime import datetime, timedelta

# List of project directories
PROJECTS = [
    r"c:\laragon\www\python-messaging-suite",
    r"c:\laragon\www\php-messaging-suite",
    r"c:\laragon\www\web-messaging-suite"
]

# Target file to modify for each commit

# Professional commit messages mapped to file types
COMMIT_MESSAGES = {
    # Python/Django
    "manage.py": ["Update manage.py", "Refactor command-line entry", "Improve startup script"],
    "settings.py": ["Update Django settings", "Refactor settings structure", "Add new config option"],
    "views.py": ["Update view logic", "Refactor view functions", "Improve view performance"],
    "urls.py": ["Update URL patterns", "Refactor routing logic", "Add new route"],
    "wsgi.py": ["Update WSGI config", "Refactor WSGI entry", "Improve deployment settings"],
    "asgi.py": ["Update ASGI config", "Refactor ASGI entry", "Improve async settings"],
    "admin.py": ["Update admin config", "Refactor admin logic", "Add new admin feature"],
    "apps.py": ["Update app config", "Refactor app structure", "Add new app"],
    "serializers.py": ["Update serializers", "Refactor serialization logic", "Add new serializer"],
    "migrations.py": ["Update migrations", "Add new migration", "Refactor migration logic"],
    "tests.py": ["Add new tests", "Update test cases", "Refactor test logic"],

    # Laravel/PHP
    "routes/web.php": ["Update web routes", "Add new route", "Refactor route logic"],
    "routes/api.php": ["Update API routes", "Add new API endpoint", "Refactor API route logic"],
    "artisan": ["Update artisan commands", "Add new command", "Refactor artisan logic"],
    ".env": ["Update environment variables", "Add new env setting", "Refactor .env file"],
    "config/app.php": ["Update app config", "Refactor app settings", "Add new config option"],
    "config/database.php": ["Update database config", "Refactor DB settings", "Add new DB option"],
    "app/Http/Controllers": ["Update controller logic", "Add new controller", "Refactor controller"],
    "app/Models": ["Update model logic", "Add new model", "Refactor model"],
    "app/Providers": ["Update provider logic", "Add new provider", "Refactor provider"],
    "resources/views": ["Update Blade templates", "Add new view", "Refactor view layout"],
    "resources/lang": ["Update language files", "Add new translation", "Refactor language structure"],
    "public/index.php": ["Update public entry", "Refactor public index", "Improve public bootstrap"],
    "bootstrap/app.php": ["Update bootstrap config", "Refactor bootstrap logic", "Improve app bootstrap"],
    "database/migrations": ["Update migration files", "Add new migration", "Refactor migration logic"],
    "database/seeders": ["Update seeder files", "Add new seeder", "Refactor seeder logic"],
    "composer.lock": ["Update composer lock", "Sync dependencies", "Refactor lock file"],

    # Vue
    "components": ["Update Vue component", "Add new component", "Refactor component logic"],
    "assets": ["Update asset files", "Add new asset", "Refactor asset structure"],
    "store/index.js": ["Update Vuex store", "Refactor store logic", "Add new store module"],
    "store/modules": ["Update Vuex modules", "Add new module", "Refactor module logic"],
    "src/App.vue": ["Update main App.vue", "Refactor App.vue", "Improve app layout"],
    "src/main.js": ["Update main.js", "Refactor main entry", "Improve startup logic"],
    "src/router/index.js": ["Update router config", "Add new route", "Refactor router logic"],
    "src/store/index.js": ["Update store config", "Refactor store logic", "Add new store module"],
    "src/components": ["Update src component", "Add new src component", "Refactor src component logic"],
    "src/views": ["Update src view", "Add new src view", "Refactor src view logic"],
    "src/assets": ["Update src asset", "Add new src asset", "Refactor src asset logic"],
    "README.md": [
        "Update documentation",
        "Improve project overview",
        "Add usage instructions",
        "Refine setup guide",
        "Fix typos in documentation",
        "Add license information",
        "Update contact details"
    ],
    "requirements.txt": [
        "Update dependencies",
        "Add new package",
        "Remove unused dependencies",
        "Fix dependency version constraints"
    ],
    "composer.json": [
        "Update PHP dependencies",
        "Add new PHP package",
        "Remove unused PHP dependencies",
        "Fix PHP dependency version constraints"
    ],
    "package.json": [
        "Update npm dependencies",
        "Add new npm package",
        "Remove unused npm dependencies",
        "Fix npm dependency version constraints"
    ],
    "main.py": [
        "Refactor main entry point",
        "Improve app initialization",
        "Add error handling",
        "Update routing logic",
        "Optimize startup performance"
    ],
    "index.php": [
        "Refactor main PHP entry",
        "Improve PHP initialization",
        "Add error handling to PHP",
        "Update PHP routing logic"
    ],
    "index.js": [
        "Refactor main JS entry",
        "Improve JS initialization",
        "Add error handling to JS",
        "Update JS routing logic"
    ],
    "index.html": [
        "Update HTML structure",
        "Improve HTML layout",
        "Add new HTML section",
        "Refactor HTML markup"
    ],
    "config.py": [
        "Update configuration settings",
        "Refactor config structure",
        "Add new environment variable",
        "Improve config validation"
    ],
    "models.py": [
        "Add new model",
        "Refactor model fields",
        "Improve model validation",
        "Update model relationships"
    ],
    "services": [
        "Improve service logic",
        "Refactor API integration",
        "Optimize service performance",
        "Add error reporting",
        "Update service documentation"
    ],
    "api": [
        "Update API endpoints",
        "Refactor API logic",
        "Improve request validation",
        "Add new endpoint",
        "Update API documentation"
    ],
    "database.py": [
        "Update database connection",
        "Refactor database logic",
        "Add migration script",
        "Improve transaction handling"
    ],
    "App.vue": [
        "Refactor main Vue component",
        "Improve app layout",
        "Update theme settings",
        "Optimize component performance"
    ],
    "main.js": [
        "Update app entry point",
        "Refactor initialization logic",
        "Add error handling",
        "Improve startup performance"
    ],
    "api.js": [
        "Update API calls",
        "Refactor API logic",
        "Improve error handling",
        "Add new API endpoint"
    ],
    "auth.js": [
        "Update authentication logic",
        "Refactor auth flow",
        "Improve token handling",
        "Add new auth feature"
    ],
    "style.css": [
        "Update styles",
        "Refactor CSS classes",
        "Improve responsiveness",
        "Add new theme colors"
    ],
    "views": [
        "Update view layout",
        "Refactor view logic",
        "Improve view responsiveness",
        "Add new view component"
    ],
    "router": [
        "Update router logic",
        "Refactor routes",
        "Add new route",
        "Improve navigation"
    ],
    "stores": [
        "Update store logic",
        "Refactor state management",
        "Add new store module",
        "Improve store performance"
    ]
}

# Number of commits per project
NUM_COMMITS = 200



def get_random_files(project_path, n=4):
    # File types for Python, PHP, and web projects
    file_types = [
        # Common
        "README.md", "requirements.txt", "composer.json", "package.json", "main.py", "index.php", "index.js", "index.html",
        # Python
        "config.py", "models.py", "database.py", "manage.py", "settings.py", "views.py", "urls.py", "wsgi.py", "asgi.py", "admin.py", "apps.py", "serializers.py", "migrations.py", "tests.py",
        # Laravel (PHP)
        "routes/web.php", "routes/api.php", "artisan", ".env", "config/app.php", "config/database.php", "app/Http/Controllers", "app/Models", "app/Providers", "resources/views", "resources/lang", "public/index.php", "bootstrap/app.php", "database/migrations", "database/seeders", "composer.lock",
        # Vue
        "App.vue", "main.js", "api.js", "auth.js", "style.css", "views", "router", "stores", "components", "assets", "store/index.js", "store/modules", "src/App.vue", "src/main.js", "src/router/index.js", "src/store/index.js", "src/components", "src/views", "src/assets"
    ]
    selected_types = random.sample(file_types, k=min(n, len(file_types)))
    files = []
    for file_type in selected_types:
        # Direct file types
        if file_type in ["README.md", "requirements.txt", "main.py", "config.py", "models.py", "database.py", "App.vue", "main.js", "api.js", "auth.js", "style.css"]:
            # Search for file in project_path or subfolders
            for root, dirs, fs in os.walk(project_path):
                for f in fs:
                    if f == file_type:
                        files.append((os.path.join(root, f), file_type))
                        break
        else:
            # Directory types (services, api, views, router, stores)
            for root, dirs, fs in os.walk(project_path):
                if os.path.basename(root) == file_type:
                    # Pick a random file from the directory
                    valid_exts = [".py", ".js", ".vue"]
                    candidates = [f for f in fs if any(f.endswith(ext) for ext in valid_exts)]
                    if candidates:
                        chosen = random.choice(candidates)
                        files.append((os.path.join(root, chosen), file_type))
                        break
    # Always ensure at least one file
    if not files:
        files.append((os.path.join(project_path, "README.md"), "README.md"))
    return files



def make_commit(project_path, commit_num):
    files = get_random_files(project_path, n=4)
    # Calculate commit date between Sept 2 and Jan 2
    start_date = datetime(2024, 9, 2)
    end_date = datetime(2025, 1, 2)
    total_seconds = int((end_date - start_date).total_seconds())
    seconds_offset = int(commit_num * total_seconds / NUM_COMMITS) + random.randint(0, 3600)
    commit_date = start_date + timedelta(seconds=seconds_offset)
    commit_date_str = commit_date.strftime('%a %b %d %H:%M:%S %Y +0000')

    # Make plausible changes to each file
    commit_msgs = []
    for file_path, file_type in files:
        # File modification logic by extension
        if file_path.endswith(".md"):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\nUpdate {commit_date.isoformat()} \n")
        elif file_path.endswith(".py"):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"# Commit {commit_num+1}: {commit_date.isoformat()}\n")
        elif file_path.endswith(".js"):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"// Commit {commit_num+1}: {commit_date.isoformat()}\n")
        elif file_path.endswith(".vue"):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"<!-- Commit {commit_num+1}: {commit_date.isoformat()} -->\n")
        elif file_path.endswith(".css"):
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"/* Commit {commit_num+1}: {commit_date.isoformat()} */\n")
        else:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\nUpdate {commit_date.isoformat()} \n")
        # Pick a commit message
        msg_list = COMMIT_MESSAGES.get(file_type, ["Update file"])
        commit_msgs.append(random.choice(msg_list))
        subprocess.run(["git", "add", file_path], cwd=project_path)

    # Combine commit messages for all files
    msg = "; ".join(commit_msgs)
    env = os.environ.copy()
    env["GIT_COMMITTER_DATE"] = commit_date_str
    env["GIT_AUTHOR_DATE"] = commit_date_str
    subprocess.run(["git", "commit", "-m", msg], cwd=project_path, env=env)

if __name__ == "__main__":
    GIT_NAME = "htiketun"
    GIT_EMAIL = "kohtiketun@outlook.com"
    for project in PROJECTS:
        print(f"Processing {project}...")
        # Set git config for user.name and user.email
        subprocess.run(["git", "config", "user.name", GIT_NAME], cwd=project)
        subprocess.run(["git", "config", "user.email", GIT_EMAIL], cwd=project)
        for i in range(NUM_COMMITS):
            make_commit(project, i)
        print(f"Done: {project}")
