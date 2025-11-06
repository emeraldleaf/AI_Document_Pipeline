#!/usr/bin/env python3
"""
Debug the stats endpoint issue.
Check what data is actually available.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.search_service import SearchService
from src.database import DatabaseService
from config import settings

def main():
    print("🔍 DEBUGGING STATS ISSUE")
    print("=" * 50)
    
    # Test database connection
    print("\n1. Testing Database Connection...")
    try:
        db = DatabaseService(settings.database_url)
        db_stats = db.get_statistics()
        print(f"✅ Database connected")
        print(f"📊 Database stats: {db_stats}")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Test search service
    print("\n2. Testing Search Service...")
    try:
        search_service = SearchService(settings.database_url)
        search_stats = search_service.get_statistics()
        print(f"✅ Search service connected")
        print(f"📊 Search stats: {search_stats}")
    except Exception as e:
        print(f"❌ Search service error: {e}")
        return
    
    # Check if statistics view exists
    print("\n3. Checking search_statistics view...")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM search_statistics"))
            count = result.fetchone()[0]
            print(f"✅ search_statistics view exists with {count} rows")
            
            # Get the actual data
            result = conn.execute(text("SELECT * FROM search_statistics"))
            row = result.fetchone()
            if row:
                print(f"📊 Raw stats data: {list(row)}")
            else:
                print("❌ No data in search_statistics view")
        
    except Exception as e:
        print(f"❌ Statistics view error: {e}")
    
    # Check documents table
    print("\n4. Checking documents table...")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM documents"))
            count = result.fetchone()[0]
            print(f"✅ Documents table has {count} documents")
            
            if count > 0:
                # Get sample document
                result = conn.execute(text("SELECT id, filename, category, processed_date FROM documents LIMIT 1"))
                row = result.fetchone()
                print(f"📄 Sample document: id={row[0]}, filename={row[1]}, category={row[2]}, date={row[3]}")
        
    except Exception as e:
        print(f"❌ Documents table error: {e}")

if __name__ == "__main__":
    main()