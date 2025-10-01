"""
Simple script to create migrations and run basic Django checks
"""
import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        # Use the Python executable from the error message
        python_exe = r"C:\laragon\bin\python\python-3.13\python.exe"
        if not os.path.exists(python_exe):
            python_exe = "python"  # Fallback to system python
        
        full_command = [python_exe] + command.split()[1:]  # Remove 'python' from command
        result = subprocess.run(full_command, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed to run {command}: {e}")
        return False
    return True

def main():
    print("🚀 Django Setup and Migration Script")
    print("=" * 50)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    print(f"📁 Working directory: {project_dir}")
    
    # List of commands to run
    commands = [
        ("python manage.py check --deploy", "Django deployment check"),
        ("python manage.py makemigrations", "Create migrations"),
        ("python manage.py migrate", "Apply migrations"),
        ("python manage.py check", "Final Django check"),
    ]
    
    success_count = 0
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"\n⚠️  Continuing with next command...")
    
    print(f"\n📊 Results: {success_count}/{len(commands)} commands completed successfully")
    
    if success_count == len(commands):
        print("\n🎉 All setup steps completed successfully!")
        print("You can now run your Django server with:")
        print("python manage.py runserver 8888")
    else:
        print("\n⚠️  Some steps failed. Please check the errors above.")

if __name__ == "__main__":
    main()