from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import asyncio
from datetime import datetime
import json

# Import your database connection
from app.database import get_db

class DatabaseStatusChecker:
    """Comprehensive database status and health checker"""
    
    def __init__(self):
        self.status_report = {
            "timestamp": datetime.now().isoformat(),
            "database_info": {},
            "connection_status": {},
            "schemas": {},
            "tables": {},
            "foreign_keys": [],
            "indexes": [],
            "table_sizes": {},
            "health_checks": []
        }
    
    async def check_connection_status(self, session: AsyncSession):
        """Check basic database connection and server info"""
        try:
            print("🔍 Checking Database Connection...")
            
            # Basic connection info
            queries = {
                "database_name": "SELECT current_database()",
                "current_user": "SELECT current_user",
                "server_version": "SELECT version()",
                "current_schema": "SELECT current_schema()",
                "session_user": "SELECT session_user",
                "connection_count": """
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """,
                "database_size": """
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """
            }
            
            for key, query in queries.items():
                try:
                    result = await session.execute(text(query))
                    value = result.scalar()
                    self.status_report["database_info"][key] = str(value)
                    print(f"  ✅ {key}: {value}")
                except Exception as e:
                    self.status_report["database_info"][key] = f"Error: {str(e)}"
                    print(f"  ❌ {key}: Error - {str(e)}")
            
            self.status_report["connection_status"]["status"] = "connected"
            print("  ✅ Database connection: HEALTHY")
            
        except Exception as e:
            self.status_report["connection_status"]["status"] = "failed"
            self.status_report["connection_status"]["error"] = str(e)
            print(f"  ❌ Database connection: FAILED - {str(e)}")
    
    async def check_schemas(self, session: AsyncSession):
        """Check all schemas in the database"""
        try:
            print("\n🏗️  Checking Database Schemas...")
            
            result = await session.execute(text("""
                SELECT 
                    schema_name,
                    schema_owner,
                    CASE 
                        WHEN schema_name IN ('information_schema', 'pg_catalog', 'pg_toast') 
                        THEN 'system' 
                        ELSE 'user' 
                    END as schema_type
                FROM information_schema.schemata 
                ORDER BY schema_type, schema_name
            """))
            
            schemas = result.fetchall()
            
            for schema_name, owner, schema_type in schemas:
                if schema_name not in self.status_report["schemas"]:
                    self.status_report["schemas"][schema_name] = {
                        "owner": owner,
                        "type": schema_type,
                        "table_count": 0,
                        "tables": []
                    }
                
                print(f"  📁 {schema_name} ({schema_type}) - Owner: {owner}")
            
            # Check for your expected schema
            expected_schema = "portfolio_pro_app"
            if expected_schema in self.status_report["schemas"]:
                print(f"  ✅ Expected schema '{expected_schema}' found!")
            else:
                print(f"  ❌ Expected schema '{expected_schema}' NOT FOUND!")
                self.status_report["health_checks"].append({
                    "check": "expected_schema",
                    "status": "failed",
                    "message": f"Schema '{expected_schema}' does not exist"
                })
            
        except Exception as e:
            print(f"  ❌ Error checking schemas: {str(e)}")
            self.status_report["health_checks"].append({
                "check": "schema_check",
                "status": "error",
                "message": str(e)
            })
    
    async def check_tables(self, session: AsyncSession):
        """Check all tables across all schemas"""
        try:
            print("\n📋 Checking Database Tables...")
            
            result = await session.execute(text("""
                SELECT 
                    t.table_schema,
                    t.table_name,
                    t.table_type,
                    obj_description(c.oid) as table_comment,
                    pg_size_pretty(pg_total_relation_size(c.oid)) as table_size,
                    pg_stat_get_tuples_fetched(c.oid) as reads,
                    pg_stat_get_tuples_inserted(c.oid) as inserts,
                    pg_stat_get_tuples_updated(c.oid) as updates,
                    pg_stat_get_tuples_deleted(c.oid) as deletes
                FROM information_schema.tables t
                LEFT JOIN pg_class c ON c.relname = t.table_name
                LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
                WHERE t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY t.table_schema, t.table_name
            """))
            
            tables = result.fetchall()
            
            if not tables:
                print("  ❌ No user tables found in database!")
                self.status_report["health_checks"].append({
                    "check": "table_existence",
                    "status": "failed", 
                    "message": "No user tables found"
                })
                return
            
            current_schema = None
            for table_info in tables:
                schema, table_name, table_type, comment, size, reads, inserts, updates, deletes = table_info
                
                if schema != current_schema:
                    print(f"\n  📁 Schema: {schema}")
                    current_schema = schema
                
                # Update schema info
                if schema in self.status_report["schemas"]:
                    self.status_report["schemas"][schema]["table_count"] += 1
                    self.status_report["schemas"][schema]["tables"].append(table_name)
                
                # Store table info
                full_table_name = f"{schema}.{table_name}"
                self.status_report["tables"][full_table_name] = {
                    "schema": schema,
                    "name": table_name,
                    "type": table_type,
                    "comment": comment,
                    "size": size,
                    "stats": {
                        "reads": reads or 0,
                        "inserts": inserts or 0,
                        "updates": updates or 0,
                        "deletes": deletes or 0
                    }
                }
                
                print(f"    📄 {table_name} ({table_type}) - Size: {size}")
                if reads or inserts or updates or deletes:
                    print(f"        Stats: R:{reads} I:{inserts} U:{updates} D:{deletes}")
            
            # Check for expected tables
            expected_tables = [
                "portfolio_pro_app.users",
                "portfolio_pro_app.notifications",
                "portfolio_pro_app.user_devices", 
                "portfolio_pro_app.user_settings"
            ]
            
            missing_tables = [t for t in expected_tables if t not in self.status_report["tables"]]
            if missing_tables:
                print(f"\n  ❌ Missing expected tables:")
                for table in missing_tables:
                    print(f"    - {table}")
                self.status_report["health_checks"].append({
                    "check": "expected_tables",
                    "status": "failed",
                    "message": f"Missing tables: {missing_tables}"
                })
            else:
                print(f"\n  ✅ All expected tables found!")
                
        except Exception as e:
            print(f"  ❌ Error checking tables: {str(e)}")
            self.status_report["health_checks"].append({
                "check": "table_check",
                "status": "error", 
                "message": str(e)
            })
    
    async def check_foreign_keys(self, session: AsyncSession):
        """Check foreign key relationships"""
        try:
            print("\n🔗 Checking Foreign Key Relationships...")
            
            result = await session.execute(text("""
                SELECT 
                    tc.table_schema,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name,
                    rc.update_rule,
                    rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints rc
                    ON tc.constraint_name = rc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY tc.table_schema, tc.table_name
            """))
            
            foreign_keys = result.fetchall()
            
            if not foreign_keys:
                print("  ⚠️  No foreign key relationships found")
                self.status_report["health_checks"].append({
                    "check": "foreign_keys",
                    "status": "warning",
                    "message": "No foreign key relationships found"
                })
            else:
                print(f"  Found {len(foreign_keys)} foreign key relationships:")
                
                current_table = None
                for fk in foreign_keys:
                    schema, table, column, f_schema, f_table, f_column, constraint, update_rule, delete_rule = fk
                    
                    full_table = f"{schema}.{table}"
                    if full_table != current_table:
                        print(f"\n    📄 {full_table}")
                        current_table = full_table
                    
                    print(f"      🔗 {column} → {f_schema}.{f_table}.{f_column}")
                    print(f"          Rules: UPDATE {update_rule}, DELETE {delete_rule}")
                    
                    self.status_report["foreign_keys"].append({
                        "child_table": full_table,
                        "child_column": column,
                        "parent_table": f"{f_schema}.{f_table}",
                        "parent_column": f_column,
                        "constraint_name": constraint,
                        "update_rule": update_rule,
                        "delete_rule": delete_rule
                    })
                    
        except Exception as e:
            print(f"  ❌ Error checking foreign keys: {str(e)}")
            self.status_report["health_checks"].append({
                "check": "foreign_key_check",
                "status": "error",
                "message": str(e)
            })
    
    async def check_indexes(self, session: AsyncSession):
        """Check database indexes"""
        try:
            print("\n📊 Checking Database Indexes...")
            
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_indexes 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schemaname, tablename, indexname
            """))
            
            indexes = result.fetchall()
            
            if indexes:
                current_table = None
                for idx in indexes:
                    schema, table, index_name, index_def, size = idx
                    
                    full_table = f"{schema}.{table}"
                    if full_table != current_table:
                        print(f"\n    📄 {full_table}")
                        current_table = full_table
                    
                    print(f"      📊 {index_name} - Size: {size}")
                    
                    self.status_report["indexes"].append({
                        "table": full_table,
                        "name": index_name,
                        "definition": index_def,
                        "size": size
                    })
            else:
                print("  ⚠️  No user indexes found")
                
        except Exception as e:
            print(f"  ❌ Error checking indexes: {str(e)}")
    
    async def check_table_sizes(self, session: AsyncSession):
        """Get detailed table size information"""
        try:
            print("\n💾 Analyzing Table Sizes...")
            
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
                    (SELECT count(*) FROM pg_stat_all_tables WHERE schemaname = t.schemaname AND relname = t.tablename) as row_count_estimate
                FROM pg_tables t
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            
            table_sizes = result.fetchall()
            
            if table_sizes:
                print("  📊 Tables by size (largest first):")
                for schema, table, total_size, table_size, index_size, row_count in table_sizes:
                    full_name = f"{schema}.{table}"
                    print(f"    📄 {full_name}")
                    print(f"        Total: {total_size}, Table: {table_size}, Indexes: {index_size}")
                    
                    self.status_report["table_sizes"][full_name] = {
                        "total_size": total_size,
                        "table_size": table_size, 
                        "index_size": index_size,
                        "estimated_rows": row_count
                    }
            
        except Exception as e:
            print(f"  ❌ Error checking table sizes: {str(e)}")
    
    async def generate_health_summary(self):
        """Generate overall health summary"""
        print("\n" + "=" * 60)
        print("🏥 DATABASE HEALTH SUMMARY")
        print("=" * 60)
        
        # Connection health
        if self.status_report["connection_status"].get("status") == "connected":
            print("✅ Database Connection: HEALTHY")
        else:
            print("❌ Database Connection: FAILED")
        
        # Schema health
        schema_count = len([s for s in self.status_report["schemas"] if self.status_report["schemas"][s]["type"] == "user"])
        print(f"📁 User Schemas: {schema_count}")
        
        # Table health  
        table_count = len(self.status_report["tables"])
        print(f"📋 User Tables: {table_count}")
        
        # Foreign key health
        fk_count = len(self.status_report["foreign_keys"])
        print(f"🔗 Foreign Keys: {fk_count}")
        
        # Issues summary
        failed_checks = [c for c in self.status_report["health_checks"] if c["status"] == "failed"]
        error_checks = [c for c in self.status_report["health_checks"] if c["status"] == "error"]
        warning_checks = [c for c in self.status_report["health_checks"] if c["status"] == "warning"]
        
        if failed_checks:
            print(f"\n❌ CRITICAL ISSUES ({len(failed_checks)}):")
            for check in failed_checks:
                print(f"   • {check['message']}")
        
        if error_checks:
            print(f"\n🚨 ERRORS ({len(error_checks)}):")
            for check in error_checks:
                print(f"   • {check['message']}")
        
        if warning_checks:
            print(f"\n⚠️  WARNINGS ({len(warning_checks)}):")
            for check in warning_checks:
                print(f"   • {check['message']}")
        
        if not failed_checks and not error_checks:
            print("\n🎉 DATABASE STATUS: HEALTHY!")
        
        print(f"\n📄 Full report generated at: {self.status_report['timestamp']}")
    
    async def save_report(self, filename=None):
        """Save the status report to a JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_status_report_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.status_report, f, indent=2, default=str)
            print(f"📁 Report saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving report: {str(e)}")
    
    async def run_complete_check(self, save_report=True):
        """Run all database status checks"""
        print("🚀 Starting Complete Database Status Check...")
        print("=" * 60)
        
        async for session in get_db():
            try:
                await self.check_connection_status(session)
                await self.check_schemas(session)
                await self.check_tables(session)
                await self.check_foreign_keys(session)
                await self.check_indexes(session)
                await self.check_table_sizes(session)
                
                await self.generate_health_summary()
                
                if save_report:
                    await self.save_report()
                
            except Exception as e:
                print(f"❌ Fatal error during status check: {str(e)}")
                raise
            finally:
                await session.close()

# Standalone function for easy use
async def check_database_status(save_report=True):
    """Convenience function to run database status check"""
    checker = DatabaseStatusChecker()
    await checker.run_complete_check(save_report)
    return checker.status_report

# Main execution
async def main():
    """Main function to run the database status checker"""
    try:
        await check_database_status(save_report=True)
    except KeyboardInterrupt:
        print("\n⚠️  Status check cancelled by user.")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())