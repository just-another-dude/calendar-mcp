#!/usr/bin/env python3
"""
Deployment verification script for Google Calendar MCP server.
This script checks if all necessary files and configurations are in place.
"""

import sys
from pathlib import Path


class DeploymentVerifier:
    def __init__(self):
        """Initialize deployment verifier."""
        self.project_root = Path(__file__).parent
        self.errors = []
        self.warnings = []

    def check_required_files(self):
        """Check if all required files exist."""
        print("🔍 Checking required files...")

        required_files = [
            "requirements.txt",
            "railway.toml",
            "Procfile",
            "run_server.py",
            "src/server.py",
            "src/auth.py",
            "src/models.py",
            "src/calendar_actions.py",
            "src/mcp_bridge.py",
            "src/webhook_utils.py",
            "DEPLOYMENT_GUIDE.md",
            "RAILWAY_DEPLOYMENT_CHECKLIST.md",
        ]

        all_found = True
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} - MISSING")
                self.errors.append(f"Required file missing: {file_path}")
                all_found = False

        return all_found

    def check_requirements_txt(self):
        """Check requirements.txt has necessary dependencies."""
        print("🔍 Checking requirements.txt...")

        required_packages = [
            "google-api-python-client",
            "google-auth-oauthlib",
            "google-auth-httplib2",
            "fastapi",
            "uvicorn",
            "python-dateutil",
            "pydantic",
            "requests",
            "python-dotenv",
            "cryptography",
            "mcp",
        ]

        try:
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                self.errors.append("requirements.txt not found")
                return False

            with open(requirements_file, "r") as f:
                requirements_content = f.read().lower()

            missing_packages = []
            for package in required_packages:
                if package.lower() not in requirements_content:
                    missing_packages.append(package)

            if missing_packages:
                print(f"   ❌ Missing packages: {', '.join(missing_packages)}")
                self.errors.append(
                    f"Missing required packages in requirements.txt: {missing_packages}"
                )
                return False
            else:
                print("   ✅ All required packages present")
                return True

        except Exception as e:
            self.errors.append(f"Error reading requirements.txt: {e}")
            return False

    def check_railway_config(self):
        """Check Railway configuration files."""
        print("🔍 Checking Railway configuration...")

        # Check railway.toml
        railway_toml = self.project_root / "railway.toml"
        if railway_toml.exists():
            print("   ✅ railway.toml exists")
        else:
            self.errors.append("railway.toml not found")
            return False

        # Check Procfile
        procfile = self.project_root / "Procfile"
        if procfile.exists():
            try:
                with open(procfile, "r") as f:
                    content = f.read().strip()
                if "python run_server.py" in content:
                    print("   ✅ Procfile configured correctly")
                else:
                    self.warnings.append("Procfile may not have correct start command")
            except Exception as e:
                self.warnings.append(f"Could not read Procfile: {e}")
        else:
            self.errors.append("Procfile not found")
            return False

        return True

    def check_environment_template(self):
        """Check example.env has necessary variables."""
        print("🔍 Checking environment template...")

        required_env_vars = [
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "CALENDAR_SCOPES",
            "TOKEN_FILE_PATH",
        ]

        example_env = self.project_root / "example.env"
        if example_env.exists():
            try:
                with open(example_env, "r") as f:
                    env_content = f.read()

                missing_vars = []
                for var in required_env_vars:
                    if var not in env_content:
                        missing_vars.append(var)

                if missing_vars:
                    self.warnings.append(
                        f"Missing environment variables in example.env: {missing_vars}"
                    )
                else:
                    print("   ✅ All required environment variables documented")

            except Exception as e:
                self.warnings.append(f"Could not read example.env: {e}")
        else:
            self.warnings.append(
                "example.env not found - consider creating one for documentation"
            )

        return True

    def check_mcp_endpoints(self):
        """Check if MCP endpoints are properly implemented."""
        print("🔍 Checking MCP endpoint implementation...")

        server_file = self.project_root / "src" / "server.py"
        if not server_file.exists():
            self.errors.append("src/server.py not found")
            return False

        try:
            with open(server_file, "r") as f:
                server_content = f.read()

            # Check for MCP endpoints
            required_endpoints = [
                "/mcp",
                "mcp_http_transport",
                "handle_mcp_initialize",
                "handle_mcp_tools_list",
                "handle_mcp_tool_call",
            ]

            missing_endpoints = []
            for endpoint in required_endpoints:
                if endpoint not in server_content:
                    missing_endpoints.append(endpoint)

            if missing_endpoints:
                self.errors.append(f"Missing MCP implementation: {missing_endpoints}")
                return False

            # Check for voice-optimized tools
            voice_tools = [
                "voice_book_appointment",
                "voice_check_availability",
                "voice_get_upcoming",
            ]
            found_voice_tools = sum(1 for tool in voice_tools if tool in server_content)

            if found_voice_tools >= 2:
                print("   ✅ MCP endpoints and voice tools implemented")
            else:
                self.warnings.append(
                    "Voice-optimized tools may not be fully implemented"
                )

            return True

        except Exception as e:
            self.errors.append(f"Error reading server.py: {e}")
            return False

    def check_gitignore(self):
        """Check .gitignore excludes sensitive files."""
        print("🔍 Checking .gitignore...")

        gitignore_file = self.project_root / ".gitignore"
        if gitignore_file.exists():
            try:
                with open(gitignore_file, "r") as f:
                    gitignore_content = f.read()

                sensitive_patterns = [".env", "*.json", "__pycache__", "*.log"]
                missing_patterns = []

                for pattern in sensitive_patterns:
                    if pattern not in gitignore_content:
                        missing_patterns.append(pattern)

                if missing_patterns:
                    self.warnings.append(
                        f"Consider adding to .gitignore: {missing_patterns}"
                    )
                else:
                    print("   ✅ .gitignore properly configured")

            except Exception as e:
                self.warnings.append(f"Could not read .gitignore: {e}")
        else:
            self.warnings.append(
                ".gitignore not found - create one to exclude sensitive files"
            )

        return True

    def check_test_scripts(self):
        """Check if test scripts exist."""
        print("🔍 Checking test scripts...")

        test_scripts = [
            "test_mcp_integration.py",
            "test_openai_integration.py",
            "verify_deployment.py",
        ]

        found_scripts = 0
        for script in test_scripts:
            script_path = self.project_root / script
            if script_path.exists():
                print(f"   ✅ {script}")
                found_scripts += 1
            else:
                self.warnings.append(f"Test script not found: {script}")

        if found_scripts >= 2:
            print("   ✅ Testing tools available")
        else:
            self.warnings.append(
                "Consider creating test scripts for easier deployment verification"
            )

        return True

    def run_verification(self):
        """Run all verification checks."""
        print("🚀 Running Deployment Verification")
        print("=" * 50)

        checks = [
            ("Required Files", self.check_required_files),
            ("Requirements.txt", self.check_requirements_txt),
            ("Railway Config", self.check_railway_config),
            ("Environment Template", self.check_environment_template),
            ("MCP Endpoints", self.check_mcp_endpoints),
            ("Git Configuration", self.check_gitignore),
            ("Test Scripts", self.check_test_scripts),
        ]

        results = {}
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}")
            print("-" * 30)
            results[check_name] = check_func()

        # Summary
        print("\n" + "=" * 50)
        print("🎯 DEPLOYMENT VERIFICATION SUMMARY")
        print("=" * 50)

        passed_checks = sum(1 for passed in results.values() if passed)
        total_checks = len(results)

        for check_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{check_name:20} {status}")

        print(f"\nPassed: {passed_checks}/{total_checks}")

        # Show errors and warnings
        if self.errors:
            print("\n🚨 ERRORS (must fix before deployment):")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS (recommended to fix):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")

        # Final verdict
        print("\n" + "=" * 50)
        if not self.errors:
            print("🎉 DEPLOYMENT VERIFICATION PASSED!")
            print("Your project is ready for Railway deployment!")
            print("\n🚀 Next steps:")
            print("1. Commit and push your code to GitHub")
            print("2. Follow RAILWAY_DEPLOYMENT_CHECKLIST.md")
            print("3. Deploy to Railway and configure environment variables")
            print("4. Test with test_mcp_integration.py")
            print("5. Integrate with OpenAI using test_openai_integration.py")
            return True
        else:
            print("❌ DEPLOYMENT VERIFICATION FAILED")
            print("Fix the errors above before deploying to Railway.")
            return False


def main():
    """Main function to run deployment verification."""
    print("Google Calendar MCP Server - Deployment Verification")
    print("=" * 60)

    verifier = DeploymentVerifier()
    success = verifier.run_verification()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
