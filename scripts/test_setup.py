#!/usr/bin/env python3
"""Quick test script to validate QueenBee setup."""

import sys
from pathlib import Path

# Add src to path if running directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from queenbee import __version__
        from queenbee.agents.base import BaseAgent
        from queenbee.agents.queen import QueenAgent
        from queenbee.config.loader import load_config
        from queenbee.db.connection import DatabaseManager
        from queenbee.db.models import AgentType, SessionStatus
        from queenbee.llm import OllamaClient
        from queenbee.session.manager import SessionManager
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    try:
        from queenbee.config.loader import load_config
        config = load_config("config.yaml")
        assert config.system.name == "queenbee"
        assert config.database.name == "queenbee"
        assert config.ollama.model
        print(f"  ✓ Configuration loaded successfully")
        print(f"    - System: {config.system.name} v{config.system.version}")
        print(f"    - Database: {config.database.host}:{config.database.port}/{config.database.name}")
        print(f"    - Ollama: {config.ollama.host} (model: {config.ollama.model})")
        return True
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False


def test_ollama():
    """Test Ollama connection."""
    print("Testing Ollama connection...")
    try:
        from queenbee.config.loader import load_config
        from queenbee.llm import OllamaClient
        
        config = load_config("config.yaml")
        ollama = OllamaClient(config.ollama)
        
        if not ollama.is_available():
            print(f"  ⚠️  Ollama not available at {config.ollama.host}")
            print("     Make sure Docker is running: docker-compose -f docker-compose.local.yml up -d")
            return False
        
        models = ollama.list_models()
        print(f"  ✓ Ollama connected successfully")
        print(f"    - Available models: {', '.join(models) if models else 'none'}")
        
        if config.ollama.model not in [m.split(':')[0] for m in models]:
            print(f"  ⚠️  Model {config.ollama.model} not found")
            print(f"     Run: docker exec -it queenbee-ollama ollama pull {config.ollama.model}")
        
        return True
    except Exception as e:
        print(f"  ❌ Ollama test failed: {e}")
        return False


def test_database():
    """Test database connection."""
    print("Testing database connection...")
    try:
        from queenbee.config.loader import load_config
        from queenbee.db.connection import DatabaseManager
        
        config = load_config("config.yaml")
        db = DatabaseManager(config.database)
        
        with db:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                assert result["test"] == 1
        
        print("  ✓ Database connected successfully")
        
        # Check if tables exist
        with db:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                result = cursor.fetchone()
                table_count = result["count"]
        
        if table_count == 0:
            print("  ⚠️  No tables found in database")
            print("     Run: python scripts/migrate.py")
            return False
        else:
            print(f"    - Found {table_count} tables")
        
        return True
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        print("     Make sure PostgreSQL is running and migrations are applied")
        return False


def test_session():
    """Test session creation."""
    print("Testing session management...")
    try:
        from queenbee.config.loader import load_config
        from queenbee.db.connection import DatabaseManager
        from queenbee.session.manager import SessionManager
        
        config = load_config("config.yaml")
        db = DatabaseManager(config.database)
        
        with db:
            session_mgr = SessionManager(db)
            session_id = session_mgr.start_session()
            print(f"  ✓ Session created: {session_id}")
            session_mgr.end_session()
            print(f"  ✓ Session ended successfully")
        
        return True
    except Exception as e:
        print(f"  ❌ Session test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("🐝 QueenBee System Test")
    print("=" * 50)
    print()
    
    tests = [
        test_imports,
        test_config,
        test_ollama,
        test_database,
        test_session,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            results.append(False)
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! QueenBee is ready to run.")
        print("\nStart QueenBee with: queenbee")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix issues before running.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
